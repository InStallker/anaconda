#
# Copyright (C) 2019  Red Hat, Inc.
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
import unittest

from mock import Mock
from textwrap import dedent

from pyanaconda.dbus.typing import *  # pylint: disable=wildcard-import
from pyanaconda.modules.common.constants.objects import DNF_PACKAGES
from pyanaconda.modules.common.errors import InvalidValueError
from pyanaconda.modules.payload.payload_interface import PayloadInterface
from pyanaconda.modules.payload.payload import PayloadModule
from pyanaconda.modules.payload.dnf.packages.packages_interface import PackagesHandlerInterface
from pyanaconda.modules.payload.dnf.packages.constants import TIMEOUT_UNSET, RETRIES_UNSET, \
    LANGUAGES_DEFAULT, LANGUAGES_NONE
from pyanaconda.modules.payload.requirements import RequirementsModule
from pyanaconda.modules.payload.requirements_interface import RequirementsInterface
from pyanaconda.modules.common.structures.payload import Requirement
from tests.nosetests.pyanaconda_tests import check_kickstart_interface


class PayloadInterfaceTestCase(unittest.TestCase):

    def setUp(self):
        """Set up the payload module."""
        self.payload_module = PayloadModule()
        self.payload_interface = PayloadInterface(self.payload_module)

        self.package_module = self.payload_module._payload_handler._packages_handler
        self.package_interface = PackagesHandlerInterface(self.package_module)

        self.callback = Mock()
        self.package_interface.PropertiesChanged.connect(self.callback)

    def _test_kickstart(self, ks_in, ks_out):
        check_kickstart_interface(self, self.payload_interface, ks_in, ks_out)

    def kickstart_properties_test(self):
        """Test kickstart properties."""
        self.assertEqual(self.payload_interface.KickstartCommands, [])
        self.assertEqual(self.payload_interface.KickstartSections, ["packages"])
        self.assertEqual(self.payload_interface.KickstartAddons, [])

    def packages_section_empty_kickstart_test(self):
        """Test the empty packages section."""
        ks_in = """
        %packages
        %end
        """
        ks_out = """
        %packages

        %end
        """
        self._test_kickstart(ks_in, ks_out)

    def packages_section_kickstart_test(self):
        """Test the packages section."""
        ks_in = """
        %packages
        package
        @group
        @module:10
        @module2:1.5/server
        @^environment
        %end
        """
        ks_out = """
        %packages
        @^environment
        @group
        @module2:1.5/server
        @module:10
        package

        %end
        """
        self._test_kickstart(ks_in, ks_out)

    def packages_section_complex_kickstart_test(self):
        """Test the packages section with duplicates."""
        ks_in = """
        %packages
        @^environment1
        package1
        @group1
        package2

        # Only this environment will stay (last specified wins)
        @^environment2
        @group2

        # duplicates
        package2
        @group2

        # modules
        @module:4
        @module:3.5/server

        %end
        """
        # The last specified environment wins, you can't specify two environments
        # Same package or group specified twice will be deduplicated
        ks_out = """
        %packages
        @^environment2
        @group1
        @group2
        @module:3.5/server
        @module:4
        package1
        package2

        %end
        """
        self._test_kickstart(ks_in, ks_out)

    def packages_section_with_attribute_kickstart_test(self):
        """Test the packages section with attribute."""
        ks_in = """
        %packages --nocore
        %end
        """
        ks_out = """
        %packages --nocore

        %end
        """
        self._test_kickstart(ks_in, ks_out)

    def packages_section_multiple_attributes_kickstart_test(self):
        """Test the packages section with multiple attributes."""
        ks_in = """
        %packages --nocore --multilib --instLangs en_US.UTF-8

        %end
        """
        ks_out = """
        %packages --nocore --instLangs=en_US.UTF-8 --multilib

        %end
        """
        self._test_kickstart(ks_in, ks_out)

    def packages_section_excludes_kickstart_test(self):
        """Test the packages section with excludes."""
        ks_in = """
        %packages
        -vim
        %end
        """
        ks_out = """
        %packages
        -vim

        %end
        """
        self._test_kickstart(ks_in, ks_out)

    def packages_section_complex_exclude_kickstart_test(self):
        """Test the packages section with complex exclude example."""
        ks_in = """
        %packages --nocore --ignoremissing --instLangs=
        @^environment1
        @group1
        package1
        -package2
        -@group2
        @group3
        package3
        %end
        """
        ks_out = """
        %packages --nocore --ignoremissing --instLangs=
        @^environment1
        @group1
        @group3
        package1
        package3
        -@group2
        -package2

        %end
        """
        self._test_kickstart(ks_in, ks_out)

    def core_group_enabled_properties_test(self):
        self.package_interface.SetCoreGroupEnabled(True)
        self.assertEqual(self.package_interface.CoreGroupEnabled, True)
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"CoreGroupEnabled": True}, [])

    def core_group_not_set_properties_test(self):
        self.assertEqual(self.package_interface.CoreGroupEnabled, True)

    def default_environment_not_set_properties_test(self):
        self.assertEqual(self.package_interface.DefaultEnvironment, False)

    def environment_properties_test(self):
        self.package_interface.SetEnvironment("TestEnv")
        self.assertEqual(self.package_interface.Environment, "TestEnv")
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"Environment": "TestEnv"}, [])

    def environment_not_set_properties_test(self):
        self.assertEqual(self.package_interface.Environment, "")

    def groups_properties_test(self):
        self.package_interface.SetGroups(["group1", "group2"])
        self.assertEqual(self.package_interface.Groups, ["group1", "group2"])
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"Groups": ["group1", "group2"]}, [])

    def groups_not_set_properties_test(self):
        self.assertEqual(self.package_interface.Groups, [])

    def groups_properties_from_kickstart_test(self):
        ks_in = """
        %packages
        @^environment
        @module:14
        @group1
        -@group1
        -@group2
        @group3
        @group4
        @module2:3/client
        %end
        """
        self.payload_interface.ReadKickstart(ks_in)
        self.assertEqual(self.package_interface.Groups, ["module:14",
                                                         "group3", "group4",
                                                         "module2:3/client"])

    def groups_properties_to_kickstart_test(self):
        ks_out = """
        %packages
        @group1
        @group2
        @module1:2.4/server
        @module2:33

        %end
        """
        self.package_interface.SetGroups(["group2", "group1",
                                          "module1:2.4/server", "module2:33"])
        self.assertEqual(self.payload_interface.GenerateKickstart().strip(),
                         dedent(ks_out).strip())

    def packages_properties_test(self):
        self.package_interface.SetPackages(["package1", "package2"])
        self.assertEqual(self.package_interface.Packages, ["package1", "package2"])
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"Packages": ["package1", "package2"]}, [])

    def packages_not_set_properties_test(self):
        self.assertEqual(self.package_interface.Packages, [])

    def excluded_groups_properties_test(self):
        self.package_interface.SetExcludedGroups(["group1", "group2"])
        self.assertEqual(self.package_interface.ExcludedGroups, ["group1", "group2"])
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"ExcludedGroups": ["group1", "group2"]}, [])

    def excluded_groups_not_set_properties_test(self):
        self.assertEqual(self.package_interface.ExcludedGroups, [])

    def excluded_groups_properties_from_kickstart_test(self):
        ks_in = """
        %packages
        @^environment1
        @group1
        -@group2
        @group3
        -@group3
        %end
        """
        self.payload_interface.ReadKickstart(ks_in)
        self.assertEqual(self.package_interface.ExcludedGroups, ["group2", "group3"])

    def excluded_groups_properties_to_kickstart_test(self):
        ks_out = """
        %packages
        -@group1
        -@group2

        %end
        """
        self.package_interface.SetExcludedGroups(["group2", "group1"])
        self.assertEqual(self.payload_interface.GenerateKickstart().strip(),
                         dedent(ks_out).strip())

    def excluded_packages_properties_test(self):
        self.package_interface.SetExcludedPackages(["package1", "package2"])
        self.assertEqual(self.package_interface.ExcludedPackages, ["package1", "package2"])
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"ExcludedPackages": ["package1", "package2"]}, [])

    def excluded_packages_not_set_properties_test(self):
        self.assertEqual(self.package_interface.ExcludedPackages, [])

    def docs_excluded_properties_test(self):
        self.package_interface.SetDocsExcluded(True)
        self.assertEqual(self.package_interface.DocsExcluded, True)
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"DocsExcluded": True}, [])

    def docs_excluded_not_set_properties_test(self):
        self.assertEqual(self.package_interface.DocsExcluded, False)

    def weakdeps_excluded_properties_test(self):
        self.package_interface.SetWeakdepsExcluded(True)
        self.assertEqual(self.package_interface.WeakdepsExcluded, True)
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"WeakdepsExcluded": True}, [])

    def weakdeps_excluded_not_set_properties_test(self):
        self.assertEqual(self.package_interface.WeakdepsExcluded, False)

    def missing_ignored_properties_test(self):
        self.package_interface.SetMissingIgnored(True)
        self.assertEqual(self.package_interface.MissingIgnored, True)
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"MissingIgnored": True}, [])

    def missing_ignored_not_set_properties_test(self):
        self.assertEqual(self.package_interface.MissingIgnored, False)

    def languages_properties_test(self):
        self.package_interface.SetLanguages("en, es")
        self.assertEqual(self.package_interface.Languages, "en, es")
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"Languages": "en, es"}, [])

    def languages_not_set_properties_test(self):
        self.assertEqual(self.package_interface.Languages, LANGUAGES_DEFAULT)

    def languages_incorrect_value_properties_test(self):
        with self.assertRaises(InvalidValueError):
            self.package_interface.SetLanguages("")

    def languages_none_properties_from_kickstart_test(self):
        ks_in = """
        %packages --instLangs=
        %end
        """
        self.payload_interface.ReadKickstart(ks_in)
        self.assertEqual(self.package_interface.Languages, LANGUAGES_NONE)

    def languages_all_properties_from_kickstart_test(self):
        ks_in = """
        %packages
        %end
        """
        self.payload_interface.ReadKickstart(ks_in)
        self.assertEqual(self.package_interface.Languages, LANGUAGES_DEFAULT)

    def multilib_policy_properties_test(self):
        self.package_interface.SetMultilibPolicy('all')
        self.assertEqual(self.package_interface.MultilibPolicy, 'all')
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"MultilibPolicy": 'all'}, [])

    def multilib_policy_not_set_properties_test(self):
        self.assertEqual(self.package_interface.MultilibPolicy, 'best')

    def timeout_properties_test(self):
        self.package_interface.SetTimeout(60)
        self.assertEqual(self.package_interface.Timeout, 60)
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"Timeout": 60}, [])

    def timeout_not_set_properties_test(self):
        self.assertEqual(self.package_interface.Timeout, TIMEOUT_UNSET)

    def retries_properties_test(self):
        self.package_interface.SetRetries(30)
        self.assertEqual(self.package_interface.Retries, 30)
        self.callback.assert_called_once_with(
            DNF_PACKAGES.interface_name, {"Retries": 30}, [])

    def retries_not_set_properties_test(self):
        self.assertEqual(self.package_interface.Retries, RETRIES_UNSET)


class PayloadRequirementsInterfaceTestCase(unittest.TestCase):

    def setUp(self):
        self.requirements_module = RequirementsModule()
        self.requirements_interface = RequirementsInterface(self.requirements_module)

    def _test_requirements(self, data, ids, reasons, strong):
        requirements = Requirement.from_structure_list(data)
        res_ids = [req.id for req in requirements]
        variant_ids = [get_variant(Str, req_id) for req_id in ids]

        self.assertEqual(variant_ids, res_ids)
        self.assertFalse(self.requirements_interface.Empty)

        for req in requirements:
            self.assertEqual(get_variant(Bool, strong), req.strong)
            reason = reasons[req.id.get_string()]
            self.assertEqual(get_variant(List[Str], reason), req.reasons)

    def _test_is_strong(self, req_data, request_id, strong):
        reqs = Requirement.from_structure_list(req_data)

        for req in reqs:
            if req.id.get_string() == request_id:
                if strong:
                    self.assertTrue(req.strong)
                else:
                    self.assertFalse(req.strong)
                break

    def empty_test(self):
        self.assertTrue(self.requirements_interface.Empty)

    def packages_simple_test(self):
        packages = ["bee", "snake", "dragon"]
        reason = "ZOO is here"
        reasons_dict = {package: [reason] for package in packages}
        strong = True

        self.requirements_interface.AddPackages(packages, reason, strong)

        requirements_data = self.requirements_interface.Packages

        self.assertEqual(3, len(requirements_data))

        self._test_requirements(requirements_data, packages, reasons_dict, strong)

    def packages_multiple_reasons_test(self):
        packages = ["bee", "snake", "dragon"]
        reason1 = "ZOO is here"
        reason2 = "Zoo is elsewhere now"
        reasons_dict = {package: [reason1] for package in packages}
        # add another reason for existing package
        reasons_dict["snake"].append(reason2)

        self.requirements_interface.AddPackages(packages, reason1, True)
        # package will be deduplicated with a second reason
        self.requirements_interface.AddPackages(["snake"], reason2, False)

        requirements_data = self.requirements_interface.Packages

        self.assertEqual(3, len(requirements_data))

        self._test_requirements(requirements_data, packages, reasons_dict, True)

    def packages_strong_reason_test(self):
        self.requirements_interface.AddPackages(["pegas"], "because he's flying", False)

        req_data = self.requirements_interface.Packages
        self._test_is_strong(req_data, "pegas", False)

        self.requirements_interface.AddPackages(["pegas"], "Still it's flying!", True)

        req_data = self.requirements_interface.Packages
        self._test_is_strong(req_data, "pegas", True)

        self.requirements_interface.AddPackages(["dragon"], "Flames!", False)

        req_data = self.requirements_interface.Packages
        self._test_is_strong(req_data, "dragon", False)
        self._test_is_strong(req_data, "pegas", True)

    def groups_simple_test(self):
        packages = ["@hive", "@nest", "@lair"]
        reason = "ZOO has nice attractions"
        reasons_dict = {package: [reason] for package in packages}
        strong = False

        self.requirements_interface.AddPackages(packages, reason, strong)

        requirements_data = self.requirements_interface.Packages

        self.assertEqual(3, len(requirements_data))

        self._test_requirements(requirements_data, packages, reasons_dict, strong)

    def groups_multiple_reasons_test(self):
        packages = ["@hive", "@nest", "@lair"]
        reason1 = "ZOO is here"
        reason2 = "Zoo is elsewhere now"
        reasons_dict = {package: [reason1] for package in packages}
        # add another reason for existing group
        reasons_dict["@nest"].append(reason2)

        self.requirements_interface.AddGroups(packages, reason1, True)
        # package will be deduplicated with a second reason
        self.requirements_interface.AddGroups(["@nest"], reason2, False)

        requirements_data = self.requirements_interface.Groups

        self.assertEqual(3, len(requirements_data))

        self._test_requirements(requirements_data, packages, reasons_dict, True)

    def groups_strong_reason_test(self):
        self.requirements_interface.AddGroups(["@horde"], "Orc", False)

        req_data = self.requirements_interface.Groups
        self._test_is_strong(req_data, "@horde", False)

        self.requirements_interface.AddGroups(["@horde"], "For the Horde!", True)

        req_data = self.requirements_interface.Groups
        self._test_is_strong(req_data, "@horde", True)

        self.requirements_interface.AddGroups(["@lair"], "Dungeons", False)

        req_data = self.requirements_interface.Groups
        self._test_is_strong(req_data, "@lair", False)
        self._test_is_strong(req_data, "@horde", True)
