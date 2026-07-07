class HelpHandler:
    Help_Docs = '''HEADERFORGE HELP / ABOUT
=============================
HeaderForge creates, previews, stages, and atomically applies managed developer headers.
Managed headers are wrapped with HEADERFORGE-BEGIN and HEADERFORGE-END.

WORKFLOW
--------
1. Open Project
2. Scan
3. Select files in the Treeview
4. Edit Header Builder fields
5. Review Header / Diff / Full File
6. Stage
7. Push

PROJECT CONFIG
--------------
Each project can contain headerforge.project.json. Create or edit it from the Project Config tab.

Example:
{
  "enabled": true,
  "include_extensions": [".cs", ".au3", ".ps1"],
  "exclude_extensions": [],
  "ignore_directories": ["bin", "obj", ".git", "node_modules"],
  "ignore_files": ["AssemblyInfo.cs"],
  "ignore_globs": ["*.generated.cs", "*.designer.cs", "*.bak"],
  "plugins_enabled": true,
  "project_plugins_directory": "headerforge_plugins",
  "header_defaults": {"owner": "Philip Otter", "build_stage": "Beta"},
  "template_lines": []
}

CONFIG KEYS
-----------
include_extensions: if empty, all known extensions are eligible. If populated, only those extensions are scanned.
exclude_extensions: extensions to block.
ignore_directories: directory names skipped anywhere in the tree.
ignore_files: exact file names skipped.
ignore_globs: glob patterns skipped.
plugins_enabled: enables project plugins.
project_plugins_directory: project plugin folder.
header_defaults: project-specific header values.
template_lines: project-specific template. Empty means use global template.

PLUGIN SYSTEM
-------------
Plugins are plain Python files. Global plugins live beside this script in headerforge_plugins/*.py.
Project plugins live in <project>/headerforge_plugins/*.py.

Supported plugin functions:

register(app)
    Add UI, toolbar buttons, tabs, or text.

get_header_fields()
    Return extra fields as dictionaries:
    {"key":"change_ticket", "label":"Change Ticket", "kind":"entry", "default":""}
    {"key":"environment", "label":"Environment", "kind":"combo", "values":["Dev","Test","Prod"], "default":"Dev"}

get_template_lines(config)
    Return extra template lines, for example:
    ["; Change Ticket : {change_ticket}"]

should_ignore(path, project_root, config)
    Return True to ignore a file or folder.

alter_header_values(values, path, config)
    Change values before rendering. Return the modified dict.

render_template(values, path, config)
    Fully override the template core. Return a list of lines or a string.

PLUGIN APP API
--------------
app.add_toolbar_button(text, command)
app.add_tab(title)
app.add_text(parent, text)
app.info(title, message)
app.reload_plugins()
app.refresh_all()
app.cfg
app.project_cfg
app.project_root

SECURITY NOTE
-------------
Plugins are executable Python code. Only load trusted plugins. HeaderForge does not sandbox plugins.
'''