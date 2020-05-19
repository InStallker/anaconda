#!/bin/python3
#
# Copyright (C) 2018  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): Jiri Konecny <jkonecny@redhat.com>
#
#
# Setup mock testing environment for Anaconda.
#

import os
import sys
import subprocess

from functools import partial

from argparse import ArgumentParser, RawDescriptionHelpFormatter


DEPENDENCY_SOLVER = "dependency_solver.py"

ANACONDA_MOCK_PATH = "/anaconda"
ANACONDA_MOCK_TEMP_PATH = "/anaconda-temp"

NOSE_TESTS_PREFIX = "nosetests/"


class MockException(Exception):

    def __init__(self, message, cmd):
        msg = """When running command '{}' exception raised.
        {}
        """.format(cmd, message)
        super().__init__(msg)


def _prepare_command(mock_command):
    cmd = []
    cmd.extend(mock_command)

    return cmd


def _run_cmd_in_chroot(mock_command):
    mock_command.append('--chroot')
    mock_command.append('--')

    return mock_command


def _get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))


def _get_dependency_script_path():
    return _get_script_dir() + os.path.sep + DEPENDENCY_SOLVER


def _resolve_top_dir():
    script_dir = _get_script_dir()
    # go up two dirs to get top path
    top_dir = os.path.split(script_dir)[0]
    return os.path.split(top_dir)[0]


def _correct_tests_paths(paths, nose_dir_name):
    result = []

    for p in paths:
        if os.path.exists(p):
            basename = p.rsplit(nose_dir_name, maxsplit=1)[-1]

            if p != basename:
                p = os.path.join(nose_dir_name, basename)

        result.append(p)

    return result


def _check_dir_exists(path):
    if os.path.exists(path):
        print("The result dir {} must not exists!".format(path), file=sys.stderr)
        exit(1)


def _check_subprocess(cmd, error_msg, stdout_pipe=False):
    """Call external command and verify return result."""
    process_result = _call_subprocess(cmd, stdout_pipe)

    if process_result.returncode != 0:
        raise MockException(error_msg, cmd)

    return process_result


def _call_subprocess(cmd, stdout_pipe=False):
    """Call external command and return result."""
    print("Running command {}".format(cmd))

    if stdout_pipe:
        return subprocess.run(cmd, stdout=subprocess.PIPE)  # pylint: disable=subprocess-run-check
    else:
        return subprocess.run(cmd)  # pylint: disable=subprocess-run-check


def parse_args():
    parser = ArgumentParser(description="""Setup Anaconda test environment in mock.""",
                            formatter_class=RawDescriptionHelpFormatter,
                            epilog="""
You need to init mock (--init command or without main commands) before running tests.
This will install all the required packages.

Parameters can be combined so you can call:
    setup-mock-test-env.py --init --copy --run-tests --result ./result


When the init is done the mock environment stays for later use.

It is possible to connect to mock by calling:
    mock -r <mock configuration> --shell

Or copy Anaconda and start CI by:
    setup-mock-test-env.py <mock configuration> --copy --run-tests --result /tmp/result

Or update existing Anaconda in a mock and start unit tests only by:
    setup-mock-test-env.py <mock configuration> --update --run-nosetests --result /tmp/result

For further info look on the mock manual page.
""")
    parser.add_argument('mock_config', action='store', type=str, metavar='mock-config',
                        help="""
                        mock configuration file; could be specified as file path or
                        name of the file in /etc/mock without .cfg suffix
                        """)
    parser.add_argument('--uniqueext', action='store', type=str, metavar='<unique text>',
                        dest='uniqueext',
                        help="""
                        set suffix to mock chroot dir; this must be used to
                        run parallel tasks.
                        """)
    parser.add_argument('--result', action='store', type=str, metavar='folder',
                        dest='result_folder', default=None,
                        help="""
                        save test result folder from anaconda to destination folder
                        """)

    group = parser.add_argument_group(title="Main commands",
                                      description="""
One of these commands must be used. Tests commands can't be combined!
""")
    group.add_argument('--init', action='store_true', dest='init',
                       help="""initialize environment with the required packages""")
    group.add_argument('--install', '-i', metavar='<packages>', action='store', type=str,
                       dest='install',
                       help="""install additional packages to the mock""")
    group.add_argument('--install-pip', '-P', metavar='<pip packages>', action='store', type=str,
                       dest='install_pip', default=None,
                       help="""
                       install additional packages from Python Package Index repository to the
                       mock environment via the pip tool
                       """)
    group.add_argument('--no-pip', action='store_true', default=False, dest='no_pip',
                       help="""
                       do not install the default pip package set
                       """)

    group.add_argument('--release', action='store_true', dest='release',
                       help="""
                       prepare mock environment to be able to make a release from there
                       """)

    group_copy = group.add_mutually_exclusive_group()
    group_copy.add_argument('--copy', '-c', action='store_true', dest='copy',
                            help="""
                            keep existing mock and only replace Anaconda folder in it;
                            this will not re-init mock chroot
                            """)
    group_copy.add_argument('--update', '-u', action='store_true', dest='update',
                            help="""
                            keep existing mock and replace updated files in Anaconda;
                            this way you can re-run tests without autogen and configure call;
                            this will not re-init mock chroot
                            """)
    group.add_argument('--prepare', '-p', action='store_true', dest='prepare',
                       help="""
                       run configure and autogen.sh on Anaconda inside of mock
                       NOTE: -t and -n will call this automatically
                       """)

    group_tests = group.add_mutually_exclusive_group()
    group_tests.add_argument('--run-tests', '-t', action='store_true', dest='run_tests',
                             help="""
                             run anaconda tests in a mock
                             """)
    group_tests.add_argument('--run-pep8-check', '-e', action='store', nargs='*',
                             metavar='<pep8 targets>',
                             dest='pep8_targets',
                             help="""
                             run anaconda pep8 check;
                             you can specify targets (folders - path ending with '/' or files)
                             from anaconda root dir as additional parameters
                             """)
    group_tests.add_argument('--run-linter', '-l', action='store_true',
                             dest='run_linter',
                             help="""
                             run anaconda pylint check in a mock
                             """)
    group_tests.add_argument('--run-nosetests', '-n', action='store', nargs='*',
                             metavar='tests/nosetests/pyanaconda_tests/test.py',
                             dest='nose_targets',
                             help="""
                             run anaconda nosetests;
                             you can specify which tests will run by giving paths to tests files
                             from anaconda root dir as additional parameters
                             """)

    namespace = parser.parse_args()
    check_args(namespace)

    return namespace


def check_args(namespace):
    if not any([namespace.init, namespace.copy, namespace.update, namespace.prepare,
                namespace.run_tests, namespace.install, namespace.install_pip, namespace.release]):
        print("You need to specify one of the main commands!", file=sys.stderr)
        print("Run './setup-mock-test-env.py --help' for more info.", file=sys.stderr)
        exit(1)


def get_required_packages():
    """Get required packages for running Anaconda tests."""
    script = _get_dependency_script_path()
    cmd = [script]

    proc_res = _check_subprocess(cmd, "Can't call dependency_solver script.", stdout_pipe=True)

    return proc_res.stdout.decode('utf-8').strip()


def get_release_packages():
    """Get packages required to make release."""
    script = _get_dependency_script_path()
    cmd = [script, "--release"]

    proc_res = _check_subprocess(cmd, "Can't call dependency_solver script.", stdout_pipe=True)

    return proc_res.stdout.decode('utf-8').strip()


def get_required_pip_packages():
    """Get pip packages for running Anaconda tests."""
    script = _get_dependency_script_path()
    cmd = [script, "--pip"]

    proc_res = _check_subprocess(cmd, "Can't call dependency_solver script.", stdout_pipe=True)

    return proc_res.stdout.decode('utf-8').strip()


def install_required_packages(mock_command, release=False):
    packages = get_required_packages()

    if release:
        release_packages = get_release_packages()
        packages = " ".join([packages, release_packages])

    install_packages_to_mock(mock_command, packages)


def install_required_pip_packages(mock_command):
    packages = get_required_pip_packages()
    if packages:
        install_pip_packages_to_mock(mock_command, packages)


def create_dir_in_mock(mock_command, path):
    cmd = _prepare_command(mock_command)

    cmd = _run_cmd_in_chroot(cmd)
    cmd.append('mkdir ' + path)

    _check_subprocess(cmd, "Can't create directory {} to the mock.".format(path))


def remove_anaconda_in_mock(mock_command, target_mock_path=ANACONDA_MOCK_PATH):
    cmd = _prepare_command(mock_command)

    cmd = _run_cmd_in_chroot(cmd)
    cmd.append('rm -rf ' + target_mock_path)

    _check_subprocess(cmd, "Can't remove existing Anaconda.")


def copy_anaconda_to_mock(mock_command, target_mock_path=ANACONDA_MOCK_PATH):
    remove_anaconda_in_mock(mock_command, target_mock_path)

    anaconda_dir = _resolve_top_dir()

    cmd = _prepare_command(mock_command)

    cmd.append('--copyin')
    cmd.append('{}'.format(anaconda_dir))
    cmd.append(target_mock_path)

    _check_subprocess(cmd, "Can't copy Anaconda to mock.")


def update_anaconda_in_mock(mock_command):
    copy_anaconda_to_mock(mock_command, ANACONDA_MOCK_TEMP_PATH)

    cmd = _prepare_command(mock_command)
    cmd = _run_cmd_in_chroot(cmd)

    cmd.append('rsync')
    cmd.append('-aAHhSv')
    cmd.append('--update')
    cmd.append('--inplace')
    cmd.append(ANACONDA_MOCK_TEMP_PATH + "/")
    cmd.append(ANACONDA_MOCK_PATH + "/")

    _check_subprocess(cmd, "Can't update Anaconda in mock.")


def copy_result(mock_command, out_dir):
    cmd = _prepare_command(mock_command)

    cmd.append('--copyout')
    cmd.append('{}/result'.format(ANACONDA_MOCK_PATH))
    cmd.append(out_dir)

    _check_subprocess(cmd, "Con't copy Anaconda tests results out of mock.")


def create_mock_command(mock_conf, uniqueext):
    cmd = ['mock', '-r', mock_conf, '--enable-network']

    if uniqueext:
        cmd.append('--uniqueext')
        cmd.append(uniqueext)

    return cmd


def install_packages_to_mock(mock_command, packages):
    cmd = _prepare_command(mock_command)

    cmd.append('--install')
    cmd.extend(packages.split(" "))

    _check_subprocess(cmd, "Can't install packages to mock.")


def install_pip_packages_to_mock(mock_command, packages):
    cmd = _prepare_command(mock_command)

    cmd = _run_cmd_in_chroot(cmd)
    cmd.append(
        'python3 -m pip install --install-option="--install-scripts=/usr/bin" {}'.format(packages)
    )

    _check_subprocess(cmd, "Can't install packages via pip to mock.")


def prepare_anaconda(mock_command):
    cmd = _prepare_command(mock_command)

    cmd = _run_cmd_in_chroot(cmd)
    cmd.append('cd {} && ./autogen.sh && ./configure'.format(ANACONDA_MOCK_PATH))

    _check_subprocess(cmd, "Can't prepare anaconda in a mock.")


def run_tests(mock_command):
    cmd = _prepare_command(mock_command)

    cmd = _run_cmd_in_chroot(cmd)
    cmd.append('cd {} && make ci'.format(ANACONDA_MOCK_PATH))

    result = _call_subprocess(cmd)

    return result.returncode == 0


def run_nosetests(mock_command, targets):
    cmd = _prepare_command(mock_command)

    targets = _correct_tests_paths(targets, NOSE_TESTS_PREFIX)
    additional_args = " ".join(targets)

    cmd = _run_cmd_in_chroot(cmd)
    cmd.append('cd {} && make tests-nose-only NOSE_TESTS_ARGS="{}"'.format(ANACONDA_MOCK_PATH,
                                                                           additional_args))

    result = _call_subprocess(cmd)

    move_logs_in_mock(mock_command)

    return result.returncode == 0


def run_pep8_check(mock_command, targets):
    cmd = _prepare_command(mock_command)
    additional_args = " ".join(targets)

    cmd = _run_cmd_in_chroot(cmd)
    cmd.append('cd {} && make tests-pep8 PEP8_TARGETS="{}"'.format(ANACONDA_MOCK_PATH,
                                                                   additional_args))

    result = _call_subprocess(cmd)

    move_logs_in_mock(mock_command)

    return result.returncode == 0


def run_linter(mock_command):
    cmd = _prepare_command(mock_command)
    cmd = _run_cmd_in_chroot(cmd)
    cmd.append('cd {} && make tests-pylint'.format(ANACONDA_MOCK_PATH))

    result = _call_subprocess(cmd)

    move_logs_in_mock(mock_command)

    return result.returncode == 0


def move_logs_in_mock(mock_command):
    cmd = _prepare_command(mock_command)
    cmd = _run_cmd_in_chroot(cmd)

    cmd.append('cd {} && make grab-logs'.format(ANACONDA_MOCK_PATH))

    _check_subprocess(cmd, "Can't move logs to result folder inside of mock.")


def init_mock(mock_command):
    cmd = _prepare_command(mock_command)

    cmd.append('--init')

    _check_subprocess(cmd, "Can't initialize mock.")


def setup_mock(mock_command, no_pip, release):
    init_mock(mock_command)

    install_required_packages(mock_command, release=release)

    if not no_pip:
        install_required_pip_packages(mock_command)


def _run_tests(mock_command, namespace, should_prepare_anaconda):
    test_func = None

    if namespace.run_tests:
        test_func = partial(run_tests)
    elif namespace.nose_targets is not None:
        test_func = partial(run_nosetests, targets=namespace.nose_targets)
    elif namespace.pep8_targets is not None:
        test_func = partial(run_pep8_check, targets=namespace.pep8_targets)
    elif namespace.run_linter:
        test_func = partial(run_linter)

    if test_func is None:
        return True

    if should_prepare_anaconda:
        prepare_anaconda(mock_command)

    return test_func(mock_command=mock_command)


if __name__ == "__main__":
    ns = parse_args()

    mock_cmd = create_mock_command(ns.mock_config, ns.uniqueext)
    anaconda_prepare_requested = False

    # quit immediately if the result dir exists
    if ns.result_folder:
        _check_dir_exists(ns.result_folder)

    if ns.init:
        setup_mock(mock_cmd, ns.no_pip, ns.release)

    if ns.install:
        install_packages_to_mock(mock_cmd, ns.install)

    if ns.install_pip:
        install_pip_packages_to_mock(mock_cmd, ns.install_pip)

    if ns.copy:
        copy_anaconda_to_mock(mock_cmd)
        anaconda_prepare_requested = True

    if ns.update:
        update_anaconda_in_mock(mock_cmd)
        anaconda_prepare_requested = False

    if ns.prepare:
        prepare_anaconda(mock_cmd)
        anaconda_prepare_requested = False

    if ns.release:
        # Zanata was removed but I don't want to change API. This can be handy in the future.
        pass

    success = _run_tests(mock_cmd, ns, anaconda_prepare_requested)

    if ns.result_folder:
        copy_result(mock_cmd, ns.result_folder)

    if not success:
        print("\nTESTS FAILED!\n")
        sys.exit(1)
