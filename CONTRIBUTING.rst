============
Contributing
============

Bug reports, questions and pull requests are welcome.


Reporting issues
================

Open an issue on GitHub with:

* the versions of SerialLibrary, Robot Framework, pySerial and Python, and
  the operating system,
* the port used (real device, USB adapter, ``loop://``, ``socket://``...),
* a minimal test case and the error message, or the relevant part of
  ``log.html``.

Questions are also welcome on the `Robot Framework Slack
<https://slack.robotframework.org>`_ and `forum <https://forum.robotframework.org>`_.


Development setup
=================

.. code:: bash

    python -m venv .venv
    .venv/bin/pip install -e .[dev]

Run everything the CI runs before opening a pull request:

.. code:: bash

    .venv/bin/ruff check src tests tools
    .venv/bin/ruff format --check src tests tools
    .venv/bin/robocop check tests
    .venv/bin/robocop format --check tests
    .venv/bin/pytest
    .venv/bin/robot --outputdir results tests/acceptance
    .venv/bin/python tools/libdoc.py --check

``tests/hardware`` needs a real ESP32 board and is not run by the CI; run it
when touching modem lines, timeouts or anything that ``loop://`` cannot
reproduce (see the README).


Guidelines
==========

Compatibility
-------------

Existing test suites must keep working within a major version:

* keyword names, argument names and order, and error messages do not change,
* ``tests/acceptance/legacy`` is the 0.4.x test suite and is never modified:
  if a change breaks it, the change is wrong,
* a keyword or argument to remove is first deprecated: its documentation
  starts with ``*DEPRECATED*``, it logs a warning with ``logger.warn``, and it
  is removed in the next major version only.

Code
----

Keywords follow the Robot Framework `library API
<https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries>`_:

* declare keywords with ``@keyword``; the library uses
  ``auto_keywords=False``, so other methods are not exposed,
* type every argument and return value: Robot Framework converts arguments
  and Libdoc documents the types,
* raise ``robot.api.Failure`` when the system under test does not behave as
  expected (assertions) and ``robot.api.Error`` when the keyword is misused
  (unknown port, invalid argument),
* only use the public ``robot.api`` modules, not ``robot.utils`` or other
  internals,
* give each keyword one of the existing tags (``port``, ``read``, ``write``,
  ``modem lines``, ``configuration``, ``assertion``, ``system``).

Documentation
-------------

* Keyword documentation uses the Robot Framework documentation syntax: a
  one-sentence first line, then details and examples. Link to keywords and
  sections with backticks (```Add Port```, ```Encodings```).
* Regenerate ``docs/SerialLibrary.html`` with ``python tools/libdoc.py`` and
  commit it with the change. The CI fails if it is out of date.
* Add an entry to ``CHANGES.rst`` for every user-visible change.

Tests
-----

Every bug fix comes with a test that fails without it. Behaviour visible from
Robot Framework is tested in ``tests/acceptance``; internal helpers in
``tests/unit``.


Supported versions
==================

* Python: the versions supported by both Robot Framework and pySerial and not
  end-of-life. A Python version is dropped in a minor release, after its end
  of life.
* Robot Framework: the current major version, from its first release
  (``7.0``). The CI tests the oldest supported release and the latest one.
* The next Robot Framework major version is excluded (``< 8.0``) until it has
  been tested. The CI job *Robot Framework pre-release* runs the tests against
  pre-releases so that the release supporting it can be prepared before it
  is out.


Making a release
================

One-time setup, by a maintainer:

* on PyPI, add a `trusted publisher
  <https://docs.pypi.org/trusted-publishers/adding-a-publisher/>`_ for this
  repository, workflow ``release.yml``, environment ``pypi``,
* on GitHub, create the ``pypi`` environment and set *Settings > Pages >
  Source* to *GitHub Actions*.

Then, for each release:

1. Make sure the CI is green on ``develop``.
2. Set the version in ``src/SerialLibrary/version.py`` following `semantic
   versioning <https://semver.org>`_.
3. Finish the ``CHANGES.rst`` entry of the version.
4. Regenerate the documentation: ``python tools/libdoc.py``.
5. Commit, then tag and push:

   .. code:: bash

       git tag -a v1.2.3 -m "Release 1.2.3"
       git push origin develop v1.2.3

The release workflow runs the tests, checks that the tag matches the version,
publishes to PyPI and deploys the documentation to GitHub Pages. Finally,
create the GitHub release from the tag with the ``CHANGES.rst`` entry, and
announce it on the Robot Framework Slack and forum.
