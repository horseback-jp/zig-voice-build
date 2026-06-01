# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
prune_gecx_assets — Generic GECX Server Garbage Collection & Audit CLI

Enables:
  - --mode=audit: Dry-run scan that writes descriptive Markdown tables of orphans
                 (Tools, Sub-Agents, Variables) to GitHub step summaries.
  - --mode=prune: Interactive terminal actuator offering selective All, None,
                 or One-by-One manual deletions.

Source: https://github.com/horseback-jp/agent-repo-sync
"""

import argparse
import json
import os
import sys
from google.api_core.exceptions import FailedPrecondition
from cxas_scrapi import Tools
from cxas_scrapi import Agents


def fetch_local_and_live_assets(app_name, app_dir):
    """Queries GECX Cloud server and scans local repository folders to find orphaned tools, sub-agents, and variables.

    Args:
        app_name: Deployed GECX App resource name (projects/.../apps/...).
        app_dir: Path to the local application folder containing app.json.
    """
    t_client = Tools(app_name=app_name)
    a_client = Agents(app_name=app_name)

    # 1. Resolve local Git workspace directories dynamically relative to app_dir
    local_tools_dir = os.path.abspath(os.path.join(app_dir, "tools"))
    local_toolsets_dir = os.path.abspath(os.path.join(app_dir, "toolsets"))
    local_agents_dir = os.path.abspath(os.path.join(app_dir, "agents"))
    app_json_path = os.path.abspath(os.path.join(app_dir, "app.json"))

    local_tool_ids = set()
    if os.path.exists(local_tools_dir):
        for item in os.listdir(local_tools_dir):
            if os.path.isdir(os.path.join(local_tools_dir, item)):
                local_tool_ids.add(item)

    local_toolset_ids = set()
    if os.path.exists(local_toolsets_dir):
        for item in os.listdir(local_toolsets_dir):
            if os.path.isdir(os.path.join(local_toolsets_dir, item)):
                local_toolset_ids.add(item)

    local_agent_ids = set()
    if os.path.exists(local_agents_dir):
        for item in os.listdir(local_agents_dir):
            if os.path.isdir(os.path.join(local_agents_dir, item)):
                local_agent_ids.add(item)

    local_variable_names = set()
    if os.path.exists(app_json_path):
        try:
            with open(app_json_path, "r") as f:
                app_data = json.load(f)
                var_decls = app_data.get("variableDeclarations", [])
                for v in var_decls:
                    if "name" in v:
                        local_variable_names.add(v["name"])
        except Exception as e:
            print(f"[WARNING] Could not parse variables from local app.json: {e}")

    print(f"Local active tools in Git: {local_tool_ids}")
    print(f"Local active sub-agents in Git: {local_agent_ids}")
    print(f"Local active variables in Git: {local_variable_names}")

    orphans = []

    # 2. Fetch live deployed Tools from Google Cloud GECX
    print("\nFetching active deployed Tools from GECX cloud server...")
    live_tools = t_client.list_tools()
    for t in live_tools:
        system_id = t.name.split("/")[-1]
        is_toolset = "/toolsets/" in t.name

        if is_toolset:
            if system_id not in local_toolset_ids:
                orphans.append(
                    {
                        "type": "Toolset",
                        "display_name": t.display_name,
                        "system_id": system_id,
                        "resource_path": t.name,
                    }
                )
        else:
            if system_id not in local_tool_ids:
                orphans.append(
                    {
                        "type": "Tool",
                        "display_name": t.display_name,
                        "system_id": system_id,
                        "resource_path": t.name,
                    }
                )

    # 3. Fetch live deployed Sub-Agents from GECX
    print("Fetching active deployed Sub-Agents from GECX cloud server...")
    live_agents = a_client.list_agents()
    for agent in live_agents:
        system_id = agent.name.split("/")[-1]
        if system_id in ["root_agent", "root"]:
            continue

        if system_id not in local_agent_ids:
            orphans.append(
                {
                    "type": "Sub-Agent",
                    "display_name": agent.display_name,
                    "system_id": system_id,
                    "resource_path": agent.name,
                }
            )

    # 4. Fetch live Variable Declarations from GECX App metadata
    print("Fetching live Variable Declarations from GECX cloud app...")
    app_config = a_client.get_app(app_name=app_name)
    live_variables = app_config.variable_declarations or []
    for v in live_variables:
        if v.name not in local_variable_names:
            orphans.append(
                {
                    "type": "Variable",
                    "display_name": v.name,
                    "system_id": v.name,
                    "resource_path": v.name,
                }
            )

    return t_client, a_client, app_config, orphans


def run_audit(orphans):
    print(f"\n[AUDIT COMPLETED] Found {len(orphans)} orphaned GECX assets on GCP.\n")

    if not orphans:
        print("All GECX assets are perfectly in sync with Git! 0 orphans found.")
        summary_env = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_env:
            with open(summary_env, "a") as f:
                f.write("### ✅ GECX Server Alignment Audit Passed\n")
                f.write(
                    "All deployed GECX assets are perfectly aligned with Git! **0 orphans detected.**\n"
                )
        return

    table = []
    table.append(
        "| Object Type | Display Name / Variable Name | System ID / Variable Name | Git Status | Action Recommended |"
    )
    table.append(
        "| :--- | :--- | :--- | :--- | :--- |"
    )

    for o in orphans:
        row = f"| `{o['type']}` | `{o['display_name']}` | `{o['system_id']}` | ❌ **DELETED** | Prune Recommended |"
        table.append(row)

    markdown_table = "\n".join(table)

    print("GECX Orphaned Assets Audit Summary:")
    print("-----------------------------------")
    for row in table:
        print(row)

    summary_env = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_env:
        with open(summary_env, "a") as f:
            f.write("### 🚦 GECX Server Alignment Audit Warnings\n")
            f.write(
                f"The following **{len(orphans)} GECX cloud resources** have been deleted from the Git repository but still exist active on the live Google Cloud server. Pruning is recommended.\n\n"
            )
            f.write(markdown_table)
            f.write(
                "\n\n*To safely clean these up, open your terminal and execute: `python scratch/prune_gecx_assets.py --app-name <app_name> --app-dir cxas_app/jph_zig_voice_agent --mode=prune`*\n"
            )
        print("\n[INFO] Successfully wrote audit table to GitHub Step Summary.")


def run_prune(t_client, a_client, app_name, app_config, orphans):
    if not orphans:
        print("\nNo orphaned assets found on the GECX server. Nothing to prune!")
        return

    print(f"\n[AUDIT] Detected {len(orphans)} orphaned assets active on GCP GECX:")
    print("-------------------------------------------------------------------")
    for idx, o in enumerate(orphans, 1):
        print(
            f" [{idx}] {o['type']} ➔ Display Name: {o['display_name']} | ID/System Name: {o['system_id']}"
        )

    print("\nChoose an operation to proceed:")
    print(" [A] Delete ALL orphaned assets from Google Cloud")
    print(" [S] Selectively review and delete assets ONE-BY-ONE")
    print(" [N] Leave all and Exit")

    try:
        choice = input("\nSelect option (A/S/N) [N]: ").strip().upper()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting safely.")
        sys.exit(0)

    if choice == "A":
        print("\nPruning all orphaned assets...")
        updated_variables = list(app_config.variable_declarations or [])
        vars_changed = False

        for o in orphans:
            if o["type"] in ("Tool", "Toolset"):
                print(f"Deleting Tool '{o['display_name']}' ({o['system_id']})...")
                t_client.delete_tool(o["resource_path"])
                print("Successfully deleted.")
            elif o["type"] == "Sub-Agent":
                print(f"Deleting Sub-Agent '{o['display_name']}' ({o['system_id']})...")
                try:
                    a_client.delete_agent(o["resource_path"])
                    print("Successfully deleted Sub-Agent.")
                except FailedPrecondition as e:
                    print(f"\n[DEPENDENCY WARNING] Skipping deletion of Sub-Agent '{o['display_name']}'.")
                    print(f"  Reason: {e.message}")
                    print(f"  Action Required: Remove routing rules pointing to '{o['display_name']}' in the GECX Console first, then re-run the pruner.\n")
            elif o["type"] == "Variable":
                print(f"Removing Variable '{o['system_id']}' from staging config...")
                updated_variables = [v for v in updated_variables if v.name != o["system_id"]]
                vars_changed = True

        if vars_changed:
            print("\nSynchronising App variable configurations back to Google Cloud...")
            a_client.update_app(app_name=app_name, variable_declarations=updated_variables)

        print("\nGECX Server Pruning completed successfully!")

    elif choice == "S":
        print("\nInitiating Selective One-by-One review...")
        updated_variables = list(app_config.variable_declarations or [])
        vars_changed = False

        for idx, o in enumerate(orphans, 1):
            try:
                confirm = (
                    input(
                        f"➔ [{idx}/{len(orphans)}] Delete {o['type']} '{o['display_name']}' (ID: {o['system_id']})? (y/N): "
                    )
                    .strip()
                    .lower()
                )
            except (KeyboardInterrupt, EOFError):
                print("\nInterrupted. Exiting safely.")
                sys.exit(0)

            if confirm in ["y", "yes"]:
                print("Deleting...")
                if o["type"] in ("Tool", "Toolset"):
                    t_client.delete_tool(o["resource_path"])
                    print("Successfully deleted Tool.")
                elif o["type"] == "Sub-Agent":
                    try:
                        a_client.delete_agent(o["resource_path"])
                        print("Successfully deleted Sub-Agent.")
                    except FailedPrecondition as e:
                        print(f"\n[DEPENDENCY WARNING] Skipping deletion of Sub-Agent '{o['display_name']}'.")
                        print(f"  Reason: {e.message}")
                        print(f"  Action Required: Remove routing rules pointing to '{o['display_name']}' in the GECX Console first, then re-run the pruner.\n")
                elif o["type"] == "Variable":
                    updated_variables = [v for v in updated_variables if v.name != o["system_id"]]
                    vars_changed = True
                    print("Variable removed from local staging config.")
            else:
                print("Skipped.")

        if vars_changed:
            print("\nPushing updated GECX variables configuration to Google Cloud...")
            a_client.update_app(app_name=app_name, variable_declarations=updated_variables)
            print("Variables synchronised successfully.")

        print("\nSelective pruning completed.")

    else:
        print("\nOperation cancelled. No changes were made to Google Cloud GECX.")


def main():
    parser = argparse.ArgumentParser(description="GECX Server Pruner & Audit CLI")
    parser.add_argument(
        "--app-name",
        required=True,
        help="Target GECX App Resource Name (e.g. projects/<id>/locations/<region>/apps/<app_id>)",
    )
    parser.add_argument(
        "--app-dir",
        required=True,
        help="Path to your local repository GECX application folder containing app.json",
    )
    parser.add_argument(
        "--mode",
        choices=["audit", "prune"],
        default="audit",
        help="Execution mode: audit (dry-run / summary) or prune (interactive deletes).",
    )
    args = parser.parse_args()

    if not os.path.exists(args.app_dir):
        print(f"[ERROR] Local GECX app directory does not exist: {args.app_dir}")
        sys.exit(1)

    t_client, a_client, app_config, orphans = fetch_local_and_live_assets(
        args.app_name, args.app_dir
    )

    if args.mode == "audit":
        run_audit(orphans)
    elif args.mode == "prune":
        run_prune(t_client, a_client, args.app_name, app_config, orphans)


if __name__ == "__main__":
    main()
