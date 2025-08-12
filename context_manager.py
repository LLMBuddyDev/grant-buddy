import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
import copy
try:
    from info import preferred_grant_criteria as DEFAULT_PREFERRED_CRITERIA
except Exception:
    # Generic defaults if info.py is absent
    DEFAULT_PREFERRED_CRITERIA = {
        "strong_yes": [
            "SBIR", "STTR", "early-stage", "Phase I", "Phase II",
            "emerging technology", "small business innovation",
            "commercialization pathway", "technology de-risking",
            "startup-friendly", "NSF", "pilot project", "dual-use",
        ],
        "conditional_yes": {
            "technical_systems": [
                "resilient systems", "zero-trust", "autonomous", "decision-making",
                "secure data workflows", "operational AI",
            ],
            "sociotech_modeling": [
                "human decision-making", "data-informed decisions", "mission planning",
                "workflow augmentation", "data visualization",
            ],
        },
        "strong_no": [
            "urban planning", "transportation modeling", "community behavior analytics",
            "infrastructure investment", "socioeconomic planning",
        ],
    }


class ContextManager:
    def __init__(self):
        self.base_storage_dir = "user_contexts"
        self.ensure_storage_dir()

    def ensure_storage_dir(self) -> None:
        if not os.path.exists(self.base_storage_dir):
            os.makedirs(self.base_storage_dir)

    def get_user_file_path(self, workspace_key: str) -> str:
        key_hash = hashlib.sha256(workspace_key.encode()).hexdigest()[:16]
        return os.path.join(self.base_storage_dir, f"contexts_{key_hash}.json")

    def load_contexts(self, workspace_key: str) -> Dict[str, Dict]:
        if not workspace_key:
            return {}
        try:
            file_path = self.get_user_file_path(workspace_key)
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    return json.load(f)
            return {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_contexts(self, contexts: Dict[str, Dict], workspace_key: str) -> None:
        if not workspace_key:
            return
        file_path = self.get_user_file_path(workspace_key)
        with open(file_path, "w") as f:
            json.dump(contexts, f, indent=2)

    def get_context_names(self, workspace_key: str) -> List[str]:
        return list(self.load_contexts(workspace_key).keys())

    def get_context(self, name: str, workspace_key: str) -> Optional[Dict]:
        return self.load_contexts(workspace_key).get(name)

    def save_context(self, name: str, context_data: Dict, workspace_key: str) -> None:
        if not workspace_key:
            return
        contexts = self.load_contexts(workspace_key)
        context_data["last_updated"] = datetime.now().isoformat()
        contexts[name] = context_data
        self.save_contexts(contexts, workspace_key)

    def delete_context(self, name: str, workspace_key: str) -> None:
        if not workspace_key:
            return
        contexts = self.load_contexts(workspace_key)
        if name in contexts:
            del contexts[name]
            self.save_contexts(contexts, workspace_key)

    def export_context(self, name: str, workspace_key: str) -> Optional[str]:
        context = self.get_context(name, workspace_key)
        if context:
            return json.dumps(context, indent=2)
        return None

    def import_context(self, json_string: str, workspace_key: str, context_name: Optional[str] = None) -> bool:
        if not workspace_key:
            return False
        try:
            context_data = json.loads(json_string)
            if not context_name:
                context_name = context_data.get("company_name", "Imported Context")
            self.save_context(context_name, context_data, workspace_key)
            return True
        except json.JSONDecodeError:
            return False


def get_workspace_key() -> str:
    if "workspace_key" not in st.session_state:
        st.session_state.workspace_key = ""

    if not st.session_state.workspace_key:
        # Center the workspace key prompt in the main page
        st.title("🔐 Enter Your Workspace Key")
        st.caption("Choose a unique key to securely store and access your company contexts.")

        left, mid, right = st.columns([1, 2, 1])
        with mid:
            key_1 = st.text_input("Workspace Key", type="password", placeholder="Enter a unique key")
            key_2 = st.text_input("Confirm Workspace Key", type="password", placeholder="Re-enter the same key")

            st.write("\u2014")
            if st.button("Access Workspace", use_container_width=True):
                if not key_1.strip():
                    st.error("Please enter a workspace key.")
                elif key_1.strip() != key_2.strip():
                    st.error("The keys don't match.")
                else:
                    st.session_state.workspace_key = key_1.strip()
                    st.success("Workspace accessed!")
                    st.rerun()
        st.stop()

    return st.session_state.workspace_key


def create_default_context() -> Dict:
    now = datetime.now().isoformat()
    return {
        "company_name": "",
        "company_context": "",
        "preferred_grant_criteria": copy.deepcopy(DEFAULT_PREFERRED_CRITERIA),
        "created": now,
        "last_updated": now,
    }


def render_context_selector(context_manager: ContextManager):
    workspace_key = st.session_state.workspace_key
    context_names = context_manager.get_context_names(workspace_key)

    st.subheader("🏢 Company Context Management")
    if not context_names:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("No company contexts found. Create your first context below!")
            selected = None
        with col2:
            if st.button("+ New Context"):
                st.session_state.creating_new_context = True
                st.session_state.editing_context = True
    else:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            selected = st.selectbox("Select Company Context:", options=context_names, key="context_selector")
        with col2:
            if st.button("+ New Context"):
                st.session_state.creating_new_context = True
                st.session_state.editing_context = True
        with col3:
            if selected and st.button("🗑️ Delete", key="quick_delete"):
                if not st.session_state.get("confirm_delete", False):
                    st.session_state.confirm_delete = True
                    st.warning(f"Delete '{selected}'? This cannot be undone.")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Yes, Delete", key="confirm_yes"):
                            context_manager.delete_context(selected, workspace_key)
                            st.session_state.confirm_delete = False
                            st.success("Deleted!")
                            st.rerun()
                    with col_no:
                        if st.button("❌ Cancel", key="confirm_no"):
                            st.session_state.confirm_delete = False
                            st.rerun()
                else:
                    st.session_state.confirm_delete = False

    return selected


def render_context_editor(context_manager: ContextManager, context_name: Optional[str] = None):
    workspace_key = st.session_state.workspace_key

    if context_name:
        context_data = context_manager.get_context(context_name, workspace_key) or create_default_context()
        if not context_data.get("company_name"):
            context_data["company_name"] = context_name
    else:
        context_data = create_default_context()

    creating_new = st.session_state.get("creating_new_context", False)

    with st.expander("⚙️ Context Settings", expanded=creating_new or not context_name):
        if creating_new:
            st.info("Your company name will be used as the context name")
        else:
            if context_name:
                st.write(f"Context: {context_name}")

        company_name = st.text_input("Company Name:", value=context_data.get("company_name", ""))

        company_context_text = st.text_area(
            "Company Context (paragraph form)",
            value=context_data.get("company_context", ""),
            height=260,
            help="Add general background, tone, priorities, examples, and any guidance that should inform analysis.",
        )

        # Preferred grant criteria editor
        st.write("---")
        st.markdown("**🎯 Preferred Grant Criteria (affects suitability guidance)**")
        crit = context_data.get("preferred_grant_criteria") or copy.deepcopy(DEFAULT_PREFERRED_CRITERIA)
        strong_yes_str = ", ".join(crit.get("strong_yes", []))
        strong_no_str = ", ".join(crit.get("strong_no", []))
        cond_yes = crit.get("conditional_yes", {})
        tech_sys_str = ", ".join(cond_yes.get("technical_systems", []))
        socio_str = ", ".join(cond_yes.get("sociotech_modeling", []))

        col_sy, col_sn = st.columns(2)
        with col_sy:
            strong_yes_str = st.text_area(
                "Strong YES keywords (comma-separated)",
                value=strong_yes_str,
                height=100,
            )
        with col_sn:
            strong_no_str = st.text_area(
                "Strong NO keywords (comma-separated)",
                value=strong_no_str,
                height=100,
            )

        col_cy1, col_cy2 = st.columns(2)
        with col_cy1:
            tech_sys_str = st.text_area(
                "Conditional YES – technical systems (comma-separated)",
                value=tech_sys_str,
                height=100,
            )
        with col_cy2:
            socio_str = st.text_area(
                "Conditional YES – socio/organizational (comma-separated)",
                value=socio_str,
                height=100,
            )

        st.write("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💾 Save Context"):
                if not company_name.strip():
                    st.error("Please provide a company name.")
                    return None
                final_name = company_name.strip()
                # Parse criteria fields back into lists
                def _split_csv(s: str) -> List[str]:
                    return [x.strip() for x in (s or "").split(",") if x.strip()]
                updated_criteria = {
                    "strong_yes": _split_csv(strong_yes_str),
                    "conditional_yes": {
                        "technical_systems": _split_csv(tech_sys_str),
                        "sociotech_modeling": _split_csv(socio_str),
                    },
                    "strong_no": _split_csv(strong_no_str),
                }
                updated = {
                    "company_name": final_name,
                    "company_context": company_context_text.strip(),
                    "preferred_grant_criteria": updated_criteria,
                }
                context_manager.save_context(final_name, updated, workspace_key)
                st.success(f"Saved '{final_name}'!")
                st.session_state.creating_new_context = False
                st.rerun()

        with col2:
            if not creating_new and context_name:
                if st.button("📥 Export"):
                    exported = context_manager.export_context(context_name, workspace_key)
                    if exported:
                        st.download_button(
                            "⬇️ Download JSON",
                            data=exported,
                            file_name=f"{context_name.replace(' ', '_')}_context.json",
                            mime="application/json",
                        )

        with col3:
            if not creating_new and context_name:
                if st.button("🗑️ Delete", key="editor_delete"):
                    if not st.session_state.get("confirm_editor_delete", False):
                        st.session_state.confirm_editor_delete = True
                        st.warning(f"Delete '{context_name}'? This cannot be undone.")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ Yes, Delete", key="editor_confirm_yes"):
                                context_manager.delete_context(context_name, workspace_key)
                                st.session_state.confirm_editor_delete = False
                                st.success("Deleted!")
                                st.rerun()
                        with col_no:
                            if st.button("❌ Cancel", key="editor_confirm_no"):
                                st.session_state.confirm_editor_delete = False
                                st.rerun()
                    else:
                        st.session_state.confirm_editor_delete = False

        if creating_new:
            if st.button("❌ Cancel"):
                st.session_state.creating_new_context = False
                st.rerun()

    if context_name:
        return context_manager.get_context(context_name, workspace_key)
    return None


