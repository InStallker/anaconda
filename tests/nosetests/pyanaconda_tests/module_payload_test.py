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
from unittest import TestCase
from mock import patch

from pyanaconda.core.configuration.payload import PayloadHandlerType
from pyanaconda.modules.common.errors.payload import HandlerNotSetError
from pyanaconda.modules.payload.payload_interface import PayloadInterface
from pyanaconda.modules.payload.payload import PayloadModule
from pyanaconda.modules.payload.dnf.dnf import DNFHandlerModule
from pyanaconda.modules.payload.live.live_os import LiveOSHandlerModule
from pyanaconda.modules.payload.live.live_image import LiveImageHandlerModule
from pyanaconda.modules.common.constants.objects import PAYLOAD_DEFAULT, LIVE_OS_HANDLER, \
    LIVE_IMAGE_HANDLER


class PayloadInterfaceTestCase(TestCase):

    def setUp(self):
        """Set up the payload module."""
        self.payload_module = PayloadModule()
        self.payload_interface = PayloadInterface(self.payload_module)

    def kickstart_properties_test(self):
        """Test kickstart properties."""
        self.assertEqual(self.payload_interface.KickstartCommands, ['liveimg'])
        self.assertEqual(self.payload_interface.KickstartSections, ["packages"])
        self.assertEqual(self.payload_interface.KickstartAddons, [])

    def no_handler_set_test(self):
        """Test empty string is returned when no handler is set."""
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(), "")

    def generate_kickstart_without_handler_test(self):
        """Test kickstart parsing without handler set."""
        self.assertEqual(self.payload_interface.GenerateKickstart(), "")

    @patch('pyanaconda.dbus.DBus.publish_object')
    @patch('pyanaconda.modules.payload.payload.conf')
    def pick_dnf_default_handler_test(self, conf, publisher):
        """Test that dnf handler is set correctly based on the configuration value."""
        conf.payload.default_handler = PayloadHandlerType.DNF

        # invoke default payload creation
        self.payload_interface.ReadKickstart("")
        self.assertIsInstance(self.payload_module.payload_handler, DNFHandlerModule)
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(),
                         PAYLOAD_DEFAULT.object_path)
        # here the publisher is called twice because the Packages section is also published
        self.assertEqual(publisher.call_count, 2)

    @patch('pyanaconda.dbus.DBus.publish_object')
    @patch('pyanaconda.modules.payload.payload.conf')
    def pick_live_os_default_handler_test(self, conf, publisher):
        """Test that live os handler is set correctly based on the configuration value."""
        conf.payload.default_handler = PayloadHandlerType.LIVE_OS

        # invoke default payload creation
        self.payload_interface.ReadKickstart("")
        self.assertIsInstance(self.payload_module.payload_handler, LiveOSHandlerModule)
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(),
                         LIVE_OS_HANDLER.object_path)
        publisher.assert_called_once()

    @patch('pyanaconda.dbus.DBus.publish_object')
    @patch('pyanaconda.modules.payload.payload.conf')
    def pick_live_image_default_handler_test(self, conf, publisher):
        """Test that live image handler is set correctly based on the configuration value."""
        conf.payload.default_handler = PayloadHandlerType.LIVE_IMAGE

        # invoke default payload creation
        self.payload_interface.ReadKickstart("")
        self.assertIsInstance(self.payload_module.payload_handler, LiveImageHandlerModule)
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(),
                         LIVE_IMAGE_HANDLER.object_path)
        publisher.assert_called_once()

    @patch('pyanaconda.modules.payload.payload.conf')
    def failed_to_pick_default_handler_test(self, conf):
        """Test that default payload handler can't be recognized -- shouldn't happen."""
        conf.payload.default_handler = ""

        with self.assertRaises(HandlerNotSetError):
            # invoke default payload creation
            self.payload_interface.ReadKickstart("")

    @patch('pyanaconda.dbus.DBus.publish_object')
    def create_dnf_handler_test(self, publisher):
        """Test creation and publishing of the DNF handler module."""
        self.payload_interface.CreateDNFHandler()
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(),
                         PAYLOAD_DEFAULT.object_path)
        # here the publisher is called twice because the Packages section is also published
        self.assertEqual(publisher.call_count, 2)

    @patch('pyanaconda.dbus.DBus.publish_object')
    def create_live_os_handler_test(self, publisher):
        """Test creation and publishing of the Live OS handler module."""
        self.payload_interface.CreateLiveOSHandler()
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(),
                         LIVE_OS_HANDLER.object_path)
        publisher.assert_called_once()

    @patch('pyanaconda.dbus.DBus.publish_object')
    def create_live_image_handler_test(self, publisher):
        """Test creation and publishing of the Live image handler module."""
        self.payload_interface.CreateLiveImageHandler()
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(),
                         LIVE_IMAGE_HANDLER.object_path)
        publisher.assert_called_once()

    @patch('pyanaconda.dbus.DBus.publish_object')
    def create_multiple_handlers_test(self, publisher):
        """Test creating two handlers."""
        self.payload_interface.CreateDNFHandler()
        self.payload_interface.CreateLiveOSHandler()

        # The last one should win
        self.assertEqual(self.payload_interface.GetActiveHandlerPath(),
                         LIVE_OS_HANDLER.object_path)
        self.assertEqual(publisher.call_count, 3)
