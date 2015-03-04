helga-jira
===========

A helga plugin for providing links and/or descriptions of JIRA tickets. For example::

    <sduncan> can you look at API-123
    <helga> sduncan might be talking about JIRA ticket http://example.com/API-123

Regular expressions for this plugin are stored as the project key without any numbers. So in the
example above, the regular expression for 'API-123' is stored as 'API'. This plugin also responds
with multiple tickets should they be found::

    <sduncan> i'm working on API-123 and API-456
    <helga> sduncan might be talking about JIRA ticket http://example.com/API-123, http://example.com/API-456

Optionally, this plugin can use JIRA's REST API in order to show full ticket descriptions if the
setting ``JIRA_REST_API`` is set and ``JIRA_SHOW_FULL_DESCRIPTIONS`` is set to True::

    <sduncan> can you look at API-123
    <helga> [API-123] Make a new version of the API

This plugin also includes a command for adding or removing JIRA ticket patterns. Usage::

    helga jira (add_re|remove_re) <pattern>

For example::

    <sduncan> !jira add_re API
    <sduncan> API-123
    <helga> sduncan might be talking about JIRA ticket http://example.com/API-123
    <sduncan> !jira remove_re API
    <sduncan> API-123

.. important::

    This plugin requires database access


Settings
--------

``JIRA_URL``
    A URL format string for showing JIRA links. This should contain a format parameter '{ticket}'.
    (default: 'http://localhost/{ticket}')

``JIRA_REST_API``
    A URL string, if non-empty, for a JIRA REST API for the JIRA plugin to use. Much like ``JIRA_URL``,
    this should contain a format parameter '{ticket}'. Note that this requires a minmum JIRA version to
    work, one that has the updated REST api. See
    https://docs.atlassian.com/software/jira/docs/api/REST/latest/. (default: 'http://localhost/api/{ticket}')

``JIRA_SHOW_FULL_DESCRIPTION``
    A boolean, if False, only the formatted ``JIRA_URL`` will be returned for JIRA links.
    If True, a full ticket title will be shown. This requires ``JIRA_REST_API`` to be set.
    (default: False)

``JIRA_AUTH``
    A two-tuple of JIRA credentials, username and password. If empty, no authentication is used.
    (default: ('', ''))


License
-------

Copyright (c) 2015 Shaun Duncan

Licensed under an `MIT`_ license.

.. _`MIT`: https://github.com/shaunduncan/helga-jira/blob/master/LICENSE
