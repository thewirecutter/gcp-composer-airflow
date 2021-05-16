# flake8: noqa
# Disable Flake8 because of all the sphinx imports
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


# Airflow documentation build configuration file, created by
# sphinx-quickstart on Thu Oct  9 20:50:01 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.
"""Configuration of Airflow Docs"""
import glob
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader  # type: ignore[misc]

import airflow
from airflow.configuration import AirflowConfigParser, default_config_yaml
from docs.exts.docs_build.third_party_inventories import (  # pylint: disable=no-name-in-module,wrong-import-order
    THIRD_PARTY_INDEXES,
)

sys.path.append(os.path.join(os.path.dirname(__file__), 'exts'))

CONF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
INVENTORY_CACHE_DIR = os.path.join(CONF_DIR, '_inventory_cache')
ROOT_DIR = os.path.abspath(os.path.join(CONF_DIR, os.pardir))
FOR_PRODUCTION = os.environ.get('AIRFLOW_FOR_PRODUCTION', 'false') == 'true'

# By default (e.g. on RTD), build docs for `airflow` package
PACKAGE_NAME = os.environ.get('AIRFLOW_PACKAGE_NAME', 'apache-airflow')
PACKAGE_DIR: Optional[str]
if PACKAGE_NAME == 'apache-airflow':
    PACKAGE_DIR = os.path.join(ROOT_DIR, 'airflow')
    PACKAGE_VERSION = airflow.__version__
elif PACKAGE_NAME.startswith('apache-airflow-providers-'):
    from provider_yaml_utils import load_package_data  # pylint: disable=no-name-in-module

    ALL_PROVIDER_YAMLS = load_package_data()
    try:
        CURRENT_PROVIDER = next(
            provider_yaml
            for provider_yaml in ALL_PROVIDER_YAMLS
            if provider_yaml['package-name'] == PACKAGE_NAME
        )
    except StopIteration:
        raise Exception(f"Could not find provider.yaml file for package: {PACKAGE_NAME}")
    PACKAGE_DIR = CURRENT_PROVIDER['package-dir']
    PACKAGE_VERSION = 'devel'
elif PACKAGE_NAME == 'helm-chart':
    PACKAGE_DIR = os.path.join(ROOT_DIR, 'chart')
    PACKAGE_VERSION = 'devel'  # TODO do we care? probably
else:
    PACKAGE_DIR = None
    PACKAGE_VERSION = 'devel'
# Adds to environment variables for easy access from other plugins like airflow_intersphinx.
os.environ['AIRFLOW_PACKAGE_NAME'] = PACKAGE_NAME
if PACKAGE_DIR:
    os.environ['AIRFLOW_PACKAGE_DIR'] = PACKAGE_DIR
os.environ['AIRFLOW_PACKAGE_VERSION'] = PACKAGE_VERSION


# Hack to allow changing for piece of the code to behave differently while
# the docs are being built. The main objective was to alter the
# behavior of the utils.apply_default that was hiding function headers
os.environ['BUILDING_AIRFLOW_DOCS'] = 'TRUE'

# == Sphinx configuration ======================================================

# -- Project information -------------------------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

# General information about the project.
project = PACKAGE_NAME
# # The version info for the project you're documenting
version = PACKAGE_VERSION
# The full version, including alpha/beta/rc tags.
release = PACKAGE_VERSION

rst_epilog = f"""
.. |version| replace:: {version}
"""

# -- General configuration -----------------------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/configuration.html

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'provider_init_hack',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinxarg.ext',
    'sphinx.ext.intersphinx',
    'exampleinclude',
    'docroles',
    'removemarktransform',
    'sphinx_copybutton',
    'airflow_intersphinx',
    "sphinxcontrib.spelling",
    'sphinx_airflow_theme',
    'redirects',
    'substitution_extensions',
]
if PACKAGE_NAME == 'apache-airflow':
    extensions.extend(
        [
            'sphinxcontrib.jinja',
            'sphinx.ext.graphviz',
            'sphinxcontrib.httpdomain',
            'sphinxcontrib.httpdomain',
            'extra_files_with_substitutions',
            # First, generate redoc
            'sphinxcontrib.redoc',
            # Second, update redoc script
            "sphinx_script_update",
        ]
    )

if PACKAGE_NAME == "apache-airflow-providers":
    extensions.extend(
        [
            'operators_and_hooks_ref',
            'providers_packages_ref',
        ]
    )
elif PACKAGE_NAME == "helm-chart":
    extensions.append("sphinxcontrib.jinja")
elif PACKAGE_NAME == "docker-stack":
    # No extra extensions
    pass
else:
    extensions.append('autoapi.extension')
# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns: List[str]
if PACKAGE_NAME == 'apache-airflow':
    exclude_patterns = [
        # We only link to selected subpackages.
        '_api/airflow/index.rst',
        'README.rst',
    ]
elif PACKAGE_NAME.startswith('apache-airflow-providers-'):
    exclude_patterns = ['operators/_partials']
else:
    exclude_patterns = []


def _get_rst_filepath_from_path(filepath: str):
    if os.path.isdir(filepath):
        result = filepath
    elif os.path.isfile(filepath) and filepath.endswith('/__init__.py'):
        result = filepath.rpartition("/")[0]
    else:
        result = filepath.rpartition(".")[0]
    result += "/index.rst"

    result = f"_api/{os.path.relpath(result, ROOT_DIR)}"
    return result


if PACKAGE_NAME == 'apache-airflow':
    # Exclude top-level packages
    # do not exclude these top-level modules from the doc build:
    _allowed_top_level = ("exceptions.py",)

    for path in glob.glob(f"{ROOT_DIR}/airflow/*"):
        name = os.path.basename(path)
        if os.path.isfile(path) and not path.endswith(_allowed_top_level):
            exclude_patterns.append(f"_api/airflow/{name.rpartition('.')[0]}")
        browsable_packages = ["operators", "hooks", "sensors", "providers", "executors", "models", "secrets"]
        if os.path.isdir(path) and name not in browsable_packages:
            exclude_patterns.append(f"_api/airflow/{name}")
else:
    exclude_patterns.extend(
        _get_rst_filepath_from_path(f) for f in glob.glob(f"{PACKAGE_DIR}/**/example_dags/**/*.py")
    )

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# If true, keep warnings as "system message" paragraphs in the built documents.
keep_warnings = True

# -- Options for HTML output ---------------------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_airflow_theme'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
if PACKAGE_NAME == 'apache-airflow':
    html_title = "Airflow Documentation"
else:
    html_title = f"{PACKAGE_NAME} Documentation"
# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = ""

#  given, this must be the name of an image file (path relative to the
#  configuration directory) that is the favicon of the docs. Modern browsers
#  use this as the icon for tabs, windows and bookmarks. It should be a
#  Windows-style icon file (.ico), which is 16x16 or 32x32 pixels large.
html_favicon = "../airflow/www/static/pin_32.png"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
if PACKAGE_NAME == 'apache-airflow':
    html_static_path = ['apache-airflow/static']
else:
    html_static_path = []
# A list of JavaScript filename. The entry must be a filename string or a
# tuple containing the filename string and the attributes dictionary. The
# filename must be relative to the html_static_path, or a full URI with
# scheme like http://example.org/script.js.
if PACKAGE_NAME == 'apache-airflow':
    html_js_files = ['jira-links.js']
else:
    html_js_files = []
if PACKAGE_NAME == 'apache-airflow':
    html_extra_path = [
        f"{ROOT_DIR}/docs/apache-airflow/start/airflow.sh",
    ]
    html_extra_with_substituions = [
        f"{ROOT_DIR}/docs/apache-airflow/start/docker-compose.yaml",
    ]

# -- Theme configuration -------------------------------------------------------
# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    '**': [
        'version-selector.html',
        'searchbox.html',
        'globaltoc.html',
    ]
    if FOR_PRODUCTION
    else [
        'searchbox.html',
        'globaltoc.html',
    ]
}

# If false, no index is generated.
html_use_index = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = False

# Theme configuration
html_theme_options: Dict[str, Any] = {
    'hide_website_buttons': True,
}
if FOR_PRODUCTION:
    html_theme_options['navbar_links'] = [
        {'href': '/community/', 'text': 'Community'},
        {'href': '/meetups/', 'text': 'Meetups'},
        {'href': '/docs/', 'text': 'Documentation'},
        {'href': '/use-cases/', 'text': 'Use-cases'},
        {'href': '/announcements/', 'text': 'Announcements'},
        {'href': '/blog/', 'text': 'Blog'},
        {'href': '/ecosystem/', 'text': 'Ecosystem'},
    ]

# A dictionary of values to pass into the template engine’s context for all pages.
html_context = {
    # Google Analytics ID.
    # For more information look at:
    # https://github.com/readthedocs/sphinx_rtd_theme/blob/master/sphinx_rtd_theme/layout.html#L222-L232
    'theme_analytics_id': 'UA-140539454-1',
    # Variables used to build a button for editing the source code
    #
    # The path is created according to the following template:
    #
    # https://{{ github_host|default("github.com") }}/{{ github_user }}/{{ github_repo }}/
    # {{ theme_vcs_pageview_mode|default("blob") }}/{{ github_version }}{{ conf_py_path }}
    # {{ pagename }}{{ suffix }}
    #
    # More information:
    # https://github.com/readthedocs/readthedocs.org/blob/master/readthedocs/doc_builder/templates/doc_builder/conf.py.tmpl#L100-L103
    # https://github.com/readthedocs/sphinx_rtd_theme/blob/master/sphinx_rtd_theme/breadcrumbs.html#L45
    # https://github.com/apache/airflow-site/blob/91f760c/sphinx_airflow_theme/sphinx_airflow_theme/suggest_change_button.html#L36-L40
    #
    'theme_vcs_pageview_mode': 'edit',
    'conf_py_path': f'/docs/{PACKAGE_NAME}/',
    'github_user': 'apache',
    'github_repo': 'airflow',
    'github_version': 'devel',
    'display_github': 'devel',
    'suffix': '.rst',
}

# == Extensions configuration ==================================================

# -- Options for sphinxcontrib.jinjac ------------------------------------------
# See: https://github.com/tardyp/sphinx-jinja

# Jinja context
if PACKAGE_NAME == 'apache-airflow':
    deprecated_options: Dict[str, Dict[str, Tuple[str, str, str]]] = defaultdict(dict)
    for (section, key), (
        (deprecated_section, deprecated_key, since_version)
    ) in AirflowConfigParser.deprecated_options.items():
        deprecated_options[deprecated_section][deprecated_key] = section, key, since_version

    jinja_contexts = {
        'config_ctx': {"configs": default_config_yaml(), "deprecated_options": deprecated_options},
        'quick_start_ctx': {
            'doc_root_url': f'https://airflow.apache.org/docs/apache-airflow/{PACKAGE_VERSION}/'
            if FOR_PRODUCTION
            else (
                'http://apache-airflow-docs.s3-website.eu-central-1.amazonaws.com/docs/apache-airflow/latest/'
            )
        },
    }
elif PACKAGE_NAME.startswith('apache-airflow-providers-'):

    def _load_config():
        templates_dir = os.path.join(PACKAGE_DIR, 'config_templates')
        file_path = os.path.join(templates_dir, "config.yml")
        if not os.path.exists(file_path):
            return {}

        with open(file_path) as f:
            return yaml.load(f, SafeLoader)

    config = _load_config()
    if config:
        jinja_contexts = {'config_ctx': {"configs": config}}
        extensions.append('sphinxcontrib.jinja')
elif PACKAGE_NAME == 'helm-chart':

    def _str_representer(dumper, data):
        style = "|" if "\n" in data else None  # show as a block scalar if we have more than 1 line
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style)

    yaml.add_representer(str, _str_representer)

    def _format_default(value: Any) -> str:
        if value == "":
            return '""'
        if value is None:
            return '~'
        return str(value)

    def _format_examples(param_name: str, schema: dict) -> Optional[str]:
        if not schema.get("examples"):
            return None

        # Nicer to have the parameter name shown as well
        out = ""
        for ex in schema["examples"]:
            if schema["type"] == "array":
                ex = [ex]
            out += yaml.dump({param_name: ex})
        return out

    def _get_params(root_schema: dict, prefix: str = "", default_section: str = "") -> List[dict]:
        """
        Given an jsonschema objects properties dict, return a flattened list of all parameters
        from that object and any nested objects
        """
        # TODO: handle arrays? probably missing more cases too
        out = []
        for param_name, schema in root_schema.items():
            prefixed_name = f"{prefix}.{param_name}" if prefix else param_name
            section_name = schema["x-docsSection"] if "x-docsSection" in schema else default_section
            if section_name and schema["description"] and "default" in schema:
                out.append(
                    {
                        "section": section_name,
                        "name": prefixed_name,
                        "description": schema["description"],
                        "default": _format_default(schema["default"]),
                        "examples": _format_examples(param_name, schema),
                    }
                )
            if schema.get("properties"):
                out += _get_params(schema["properties"], prefixed_name, section_name)
        return out

    schema_file = os.path.join(PACKAGE_DIR, "values.schema.json")  # type: ignore
    with open(schema_file) as config_file:
        chart_schema = json.load(config_file)

    params = _get_params(chart_schema["properties"])

    # Now, split into sections
    sections: Dict[str, List[Dict[str, str]]] = {}
    for param in params:
        if param["section"] not in sections:
            sections[param["section"]] = []

        sections[param["section"]].append(param)

    # and order each section
    for section in sections.values():  # type: ignore
        section.sort(key=lambda i: i["name"])  # type: ignore

    # and finally order the sections!
    ordered_sections = []
    for name in chart_schema["x-docsSectionOrder"]:
        if name not in sections:
            raise ValueError(f"Unable to find any parameters for section: {name}")
        ordered_sections.append({"name": name, "params": sections.pop(name)})

    if sections:
        raise ValueError(f"Found section(s) which were not in `section_order`: {list(sections.keys())}")

    jinja_contexts = {"params_ctx": {"sections": ordered_sections}}


# -- Options for sphinx.ext.autodoc --------------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

# This value contains a list of modules to be mocked up. This is useful when some external dependencies
# are not met at build time and break the building process.
autodoc_mock_imports = [
    'MySQLdb',
    'adal',
    'analytics',
    'azure',
    'azure.cosmos',
    'azure.datalake',
    'azure.kusto',
    'azure.mgmt',
    'boto3',
    'botocore',
    'bson',
    'cassandra',
    'celery',
    'cloudant',
    'cryptography',
    'cx_Oracle',
    'datadog',
    'distributed',
    'docker',
    'google',
    'google_auth_httplib2',
    'googleapiclient',
    'grpc',
    'hdfs',
    'httplib2',
    'jaydebeapi',
    'jenkins',
    'jira',
    'kubernetes',
    'msrestazure',
    'pandas',
    'pandas_gbq',
    'paramiko',
    'pinotdb',
    'psycopg2',
    'pydruid',
    'pyhive',
    'pyhive',
    'pymongo',
    'pymssql',
    'pysftp',
    'qds_sdk',
    'redis',
    'simple_salesforce',
    'slack_sdk',
    'smbclient',
    'snowflake',
    'sshtunnel',
    'telegram',
    'tenacity',
    'vertica_python',
    'winrm',
    'zdesk',
]

# The default options for autodoc directives. They are applied to all autodoc directives automatically.
autodoc_default_options = {'show-inheritance': True, 'members': True}

# -- Options for sphinx.ext.intersphinx ----------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

# This config value contains names of other projects that should
# be linked to in this documentation.
# Inventories are only downloaded once by docs/exts/docs_build/fetch_inventories.py.
intersphinx_mapping = {
    pkg_name: (f"{THIRD_PARTY_INDEXES[pkg_name]}/", (f'{INVENTORY_CACHE_DIR}/{pkg_name}/objects.inv',))
    for pkg_name in [
        'boto3',
        'celery',
        'hdfs',
        'jinja2',
        'mongodb',
        'pandas',
        'python',
        'requests',
        'sqlalchemy',
    ]
}
if PACKAGE_NAME in ('apache-airflow-providers-google', 'apache-airflow'):
    intersphinx_mapping.update(
        {
            pkg_name: (
                f"{THIRD_PARTY_INDEXES[pkg_name]}/",
                (f'{INVENTORY_CACHE_DIR}/{pkg_name}/objects.inv',),
            )
            for pkg_name in [
                'google-api-core',
                'google-cloud-automl',
                'google-cloud-bigquery',
                'google-cloud-bigquery-datatransfer',
                'google-cloud-bigquery-storage',
                'google-cloud-bigtable',
                'google-cloud-container',
                'google-cloud-core',
                'google-cloud-datacatalog',
                'google-cloud-datastore',
                'google-cloud-dlp',
                'google-cloud-kms',
                'google-cloud-language',
                'google-cloud-monitoring',
                'google-cloud-pubsub',
                'google-cloud-redis',
                'google-cloud-spanner',
                'google-cloud-speech',
                'google-cloud-storage',
                'google-cloud-tasks',
                'google-cloud-texttospeech',
                'google-cloud-translate',
                'google-cloud-videointelligence',
                'google-cloud-vision',
            ]
        }
    )

# -- Options for sphinx.ext.viewcode -------------------------------------------
# See: https://www.sphinx-doc.org/es/master/usage/extensions/viewcode.html

# If this is True, viewcode extension will emit viewcode-follow-imported event to resolve the name of
# the module by other extensions. The default is True.
viewcode_follow_imported_members = True

# -- Options for sphinx-autoapi ------------------------------------------------
# See: https://sphinx-autoapi.readthedocs.io/en/latest/config.html

# Paths (relative or absolute) to the source code that you wish to generate
# your API documentation from.
autoapi_dirs = [
    PACKAGE_DIR,
]

# A directory that has user-defined templates to override our default templates.
if PACKAGE_NAME == 'apache-airflow':
    autoapi_template_dir = 'autoapi_templates'

# A list of patterns to ignore when finding files
autoapi_ignore = [
    'airflow/configuration/',
    '*/example_dags/*',
    '*/_internal*',
    '*/node_modules/*',
    '*/migrations/*',
    '*/contrib/*',
]
if PACKAGE_NAME == 'apache-airflow':
    autoapi_ignore.append('*/airflow/providers/*')
# Keep the AutoAPI generated files on the filesystem after the run.
# Useful for debugging.
autoapi_keep_files = True

# Relative path to output the AutoAPI files into. This can also be used to place the generated documentation
# anywhere in your documentation hierarchy.
autoapi_root = '_api'

# Whether to insert the generated documentation into the TOC tree. If this is False, the default AutoAPI
# index page is not generated and you will need to include the generated documentation in a
# TOC tree entry yourself.
autoapi_add_toctree_entry = False

# -- Options for ext.exampleinclude --------------------------------------------
exampleinclude_sourceroot = os.path.abspath('..')

# -- Options for ext.redirects -------------------------------------------------
redirects_file = 'redirects.txt'

# -- Options for sphinxcontrib-spelling ----------------------------------------
spelling_word_list_filename = [os.path.join(CONF_DIR, 'spelling_wordlist.txt')]

# -- Options for sphinxcontrib.redoc -------------------------------------------
# See: https://sphinxcontrib-redoc.readthedocs.io/en/stable/
if PACKAGE_NAME == 'apache-airflow':
    OPENAPI_FILE = os.path.join(
        os.path.dirname(__file__), "..", "airflow", "api_connexion", "openapi", "v1.yaml"
    )
    redoc = [
        {
            'name': 'Airflow REST API',
            'page': 'stable-rest-api-ref',
            'spec': OPENAPI_FILE,
            'opts': {
                'hide-hostname': True,
                'no-auto-auth': True,
            },
        },
    ]

    # Options for script updater
    redoc_script_url = "https://cdn.jsdelivr.net/npm/redoc@2.0.0-rc.48/bundles/redoc.standalone.js"
