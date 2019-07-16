#
# DBus interface for packaging.
#
# Copyright (C) 2018 Red Hat, Inc.
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
from pyanaconda.dbus.interface import dbus_interface
from pyanaconda.dbus.typing import *  # pylint: disable=wildcard-import

from pyanaconda.modules.common.constants.services import PAYLOAD
from pyanaconda.modules.common.base import KickstartModuleInterface


@dbus_interface(PAYLOAD.interface_name)
class PayloadInterface(KickstartModuleInterface):
    """DBus interface for Payload module."""

    def CreateLiveOSHandler(self) -> ObjPath:
        """Create Live OS payload handler and publish it on dbus."""
        self.implementation.create_live_os_handler()
        return self.implementation.get_active_handler_path()
