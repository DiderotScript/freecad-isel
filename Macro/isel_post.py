# -*- coding: utf8 -*-
# ***************************************************************************
# *   (c) SCRIPT (inge@script.univ-paris-diderot.fr) 2019                   *
# *   (c) sliptonic (shopinthewoods@gmail.com) 2014                         *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************/

from __future__ import print_function
import FreeCAD
from FreeCAD import Units
import Path
import argparse
import datetime
import shlex
from stat import S_IWRITE, S_IREAD
from os import chmod
from PathScripts import PostUtils
from PathScripts import PathUtils

TOOLTIP='''
FreeCAD Path post-processor to output code for the ISEL ICP-4030 machines.

The following code follows ISEL specification from their
'operating_instruction_remote.pdf' manual.
https://www.isel.com/en/support-downloads/manuals.html

This postprocessor, once placed in the appropriate PathScripts folder,
can be used directly from inside FreeCAD, via the GUI importer or via
python scripts with:

import isel_post
isel_post.export(object,"/path/to/file.ncp","")
'''

TODO='''
* test with FreeCAD and US inches
* test (C)CWABS command in plane XZ/YZ
* implement DRILL commands
'''

COMMAND_SPACE = " "
LINENR = -1  # line number starting value
MODE = 'absolute' # TODO: handle relative coordinates

# These globals set common customization preferences
OUTPUT_COMMENTS = True
SHOW_EDITOR = False

# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = '''; NEXT LINE IS THE MACHINE RAPID SPEED
FASTVEL 50000
PLANE XY'''

# Postamble text will appear following the last operation.
POSTAMBLE = '''SPINDLE OFF
PROGEND'''

# These globals will be reflected in the Machine configuration of the project
# By default, FreeCAD use the international metric system :
# * millimeters (mm) for axis position values liner axes
# * arc sec (") for axis position values rotary axes
# * millimeter/second (mm/s) for axis liner veolicities
# * arc sec/second ("/s) for axis pitch rate
# * revolution per minute (rpm) for spindle speed
# ISEL use :
# * micrometers (μm) for axis position values liner axes
# * arc sec (") for axis position values rotary axes
# * micrometer/second (µm/s) for axis liner veolicities
# * arc sec/second ("/s) for axis pitch rate
# * revolution per minute or second (rpm|rps) for spindle speed
UNITS = "G21"  # G21 for metric, G20 for us standard
UNIT_SPEED_FORMAT = 'mm/min'
UNIT_FORMAT = 'mm'

MACHINE_NAME = "ISEL - ICP 4030 (default)"
CORNER_MIN = {'x': 0, 'y': 0, 'z': 0}
CORNER_MAX = {'x': 500, 'y': 300, 'z': 300}

# Pre operation text will be inserted before every operation
PRE_OPERATION = ''''''

# Post operation text will be inserted after every operation
POST_OPERATION = ''''''

# Tool Change commands will be inserted before a tool change
TOOL_CHANGE = ''''''

parser = argparse.ArgumentParser(prog='isel', add_help=False)
parser.add_argument('--no-comments', action='store_true', help='suppress comment output')
parser.add_argument('--show-editor', action='store_true', help='pop up editor before writing output')
parser.add_argument('--preamble', help='set commands to be issued before the first command, default="'+PREAMBLE+'"')
parser.add_argument('--postamble', help='set commands to be issued after the last command, default="'+POSTAMBLE+'"')
parser.add_argument('--preoperation', help='set commands to be issued before each command, default="'+PRE_OPERATION+'"')
parser.add_argument('--postoperation', help='set commands to be issued after each command, default="'+POST_OPERATION+'"')
TOOLTIP_ARGS = parser.format_help()

# to distinguish python built-in open function from the one declared below
if open.__module__ in ['__builtin__','io']:
    pythonopen = open


def processArguments(argstring):
    global OUTPUT_COMMENTS
    global SHOW_EDITOR
    global PREAMBLE
    global POSTAMBLE
    global PRE_OPERATION
    global POST_OPERATION

    try:
        args = parser.parse_args(shlex.split(argstring))
        if args.no_comments:
            OUTPUT_COMMENTS = False
        if args.show_editor:
            SHOW_EDITOR = True
        if args.preamble is not None:
            PREAMBLE = args.preamble
        if args.postamble is not None:
            POSTAMBLE = args.postamble
        if args.preoperation is not None:
            PRE_OPERATION = args.preoperation
        if args.postoperation is not None:
            POST_OPERATION = args.postoperation
    except:
        return False

    return True


def export(objectslist, filename, argstring):
    if not processArguments(argstring):
        return None
    global UNITS
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT

    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print("the object " + obj.Name + " is not a path. Please select only path and Compounds.")
            return None

    print("postprocessing...")
    gcode = linenumber() + 'IMF_PBL_V1.0\n'

    # write header
    now = datetime.datetime.now()
    gcode += linenumber() + ";- Exported by FreeCAD\n"
    gcode += linenumber() + ";- Post Processor: " + __name__ + '\n'
    gcode += linenumber() + ";- Output Time:" + str(now) + '\n'

    # Write the preamble
    if OUTPUT_COMMENTS:
        gcode += linenumber() + ";- begin preamble\n"
    for line in PREAMBLE.splitlines(False):
        gcode += linenumber() + line + '\n'
    if OUTPUT_COMMENTS:
        gcode += linenumber() + ";- finish preamble\n"

    for obj in objectslist:

        # fetch machine details
        job = PathUtils.findParentJob(obj)

        myMachine = job.Machine if hasattr(job, 'Machine') else MACHINE_NAME

        # FIXME: we only operate using ISEL units (µm and µm/s)
        if hasattr(job, "MachineUnits"):
            print("Unknown parameter 'MachineUnits: "
                  "{}".format(job.MachineUnits))

        # do the pre_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + ";- begin operation: %s\n" % obj.Label
            gcode += linenumber() + ";- machine: %s\n" % myMachine
            gcode += linenumber() + ";- unit system: %s\n" % UNIT_SPEED_FORMAT
        for line in PRE_OPERATION.splitlines(True):
            gcode += linenumber() + line

        gcode += parse(obj)

        # do the post_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + ";- finish operation: %s\n" % obj.Label
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber() + line

    # do the post_amble
    if OUTPUT_COMMENTS:
        gcode += linenumber() + ";- begin postamble\n"
    for line in POSTAMBLE.splitlines(False):
        gcode += linenumber() + line + '\n'
    if OUTPUT_COMMENTS:
        gcode += linenumber() + ";- finish postamble\n"

    if FreeCAD.GuiUp and SHOW_EDITOR:
        dia = PostUtils.GCodeEditorDialog()
        dia.editor.setText(gcode)
        result = dia.exec_()
        if result:
            final = dia.editor.toPlainText()
        else:
            final = gcode
    else:
        final = gcode

    print("done postprocessing.")

    if not filename == '-':
        # Clear read-only flag set by Isel Remote
        try:
            chmod(filename, S_IWRITE|S_IREAD)
        except:
            pass # file did not exist ?
        with pythonopen(filename, "w") as f:
            f.write(final)

    return final


def linenumber():
    global LINENR
    # output line number
    LINENR += 1
    return  "N{:06d} ".format(LINENR)


def toNatural(d):
    return int(round(d))


def toUM(d):
    d = Units.Quantity(d, FreeCAD.Units.Length)
    d = d.getValueAs(UNIT_FORMAT)
    return int(d * 1000)


def toUM_sec(v):
    v = Units.Quantity(v, FreeCAD.Units.Velocity)
    v = v.getValueAs(UNIT_SPEED_FORMAT)
    return int(v * 1000 / 60)


def parse(pathobj):
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT

    out = ""

    # the order of parameters
    params = ['I', 'J', 'X', 'Y', 'Z', 'A', 'B', 'C', 'F', 'S', 'T', 'Q', 'R']

    # Keep track of the state,
    # for skipping doubles
    # and, someday, for relative coordinates
    state = {"X": -1, "Y": -1, "Z": -1, "F": 0.0}
    circle = {'I': 'X', 'J': 'Y', 'K': 'Z'}

    # If we have a compound or project.
    if hasattr(pathobj, "Group"):
        for p in pathobj.Group:
            out += parse(p)
        return out

    # else: we have a simple path ...

    # groups might contain non-path things like stock.
    if not hasattr(pathobj, "Path"):
        return out

    for c in pathobj.Path.Commands:
        command = c.Name # current command
        outstring = ['unknown_command'] # current command + arguments

        # Convert commands from the standard G-Code
        # to the ISEL dialect
        if command == "message": # FIXME: deadcode ?
            print("dead code ? " + command)
            continue # skip command
        elif command[0] == '(':
            if OUTPUT_COMMENTS:
                # Replace parenthesis by ';-'
                command = '; ' + command[1:-1]
            else:
                continue # skip command
        elif command == 'G0':
            command = 'FASTABS'
        elif command == 'G1':
            command = 'MOVEABS'
        elif command == 'G2':
            command = 'CWABS'
        elif command == 'G3':
            command = 'CCWABS'
        elif command == 'G17':
            command = 'PLANE XY'
        elif command == 'G18':
            command = 'PLANE ZX'
        elif command == 'G19':
            command = 'PLANE YZ'
        elif command == 'G80':
            # Note that G80 stand for "cancel canned cycle"
            # but we use it here to perform the actual drilling operation
            # with the "XYZ" coordinates saved in the previous command
            # (which sould be a G81/82/83 drilling cycle)
            command = 'DRILL'
        elif command == 'G81':
            command = 'DRILLDEF'
            outstring.append("C1")
        elif command == 'G82':
            command = 'DRILLDEF'
            outstring.append("C3")
        elif command == 'G83':
            command = 'DRILLDEF'
            outstring.append("C2")
        elif command == 'G94':
            command = 'VEL'
        elif command == 'M3':
            command = 'SPINDLE CW'
        elif command == 'M4':
            command = 'SPINDLE CCW'
        elif command == 'M5':
            command = 'SPINDLE OFF'
        # TODO: SPINDLE ON
        elif command == 'M6':
            command = 'GETTOOL'
            for line in TOOL_CHANGE.splitlines(True):
                out += linenumber() + line
        elif command == 'PROGBEGIN':
            command = 'PROGBEGIN'
        elif command == 'M02' or command == 'M30':
            command = 'PROGEND'
        # Coolant ON/OFF
        elif command == 'M7' or command == ' M8':
            command = 'COOLANT ON'
        elif command == 'M9':
            command = 'COOLANT OFF'
        # Workpiece clamp ON/OFF
        elif command == 'M10':
            command = 'WPCLAMP ON'
        elif command == 'M11':
            command = 'WPCLAMP OFF'
        # Pump ON/OFF
        elif command == 'PUMP ON':
            command = 'PUMP ON'
        elif command == 'PUMP OFF':
            command = 'PUMP OFF'
        # Lamp ON/OFF
        elif command == 'LAMP ON':
            command = 'LAMP ON'
        elif command == 'LAMP OFF':
            command = 'LAMP OFF'
        # Periphery option1 ON/OFF
        elif command == 'POPTION1 ON':
            command = 'POPTION1 ON'
        elif command == 'POPTION1 OFF':
            command = 'POPTION1 OFF'
        # Periphery option2 ON/OFF
        elif command == 'POPTION2 ON':
            command = 'POPTION2 ON'
        elif command == 'POPTION2 OFF':
            command = 'POPTION2 OFF'
        else:
            print("ERROR: unknown command " + command + ", skipping...")
            continue # skip to next command

        outstring[0] = command

        # Now we convert the parameters
        # from the FreeCAD unit system to the Isel one
        def sort_by_params(k):
            try:
                return params.index(k)
            except:
                return len(params) + 1
        for param in sorted(c.Parameters, key=sort_by_params):
            print('processing param {}'.format(param))
            if param == 'F':
                if (state[param] != c.Parameters[param]):
                    feedrate = toUM_sec(c.Parameters[param])
                    if feedrate > 0:
                        out += linenumber() + "VEL {0:d}\n".format(feedrate)
            elif param in "IJ": # TODO: handle "K" parameter
                # In FreeCAD internal G-Code
                # I,J and K are always relative to the last point
                last_pos = state[circle[param]]
                pos = toUM(last_pos + c.Parameters[param])
                outstring.append('{0}{1:d}'.format(param, pos))
            elif param in "R":
                # backtrack along Z axis between peck drilling cycles
                backtrack = toUM(c.Parameters[param])
                outstring.append('{0}{1:d}'.format(param, backtrack))
            elif param in "Q":
                incremental_feed = toUM(c.Parameters[param])
                # first incremental feed rate for drilling and deburring
                outstring.append('{0}{1:d}'.format("F", incremental_feed))
                # all other incremental feed rate for drilling and deburring
                outstring.append('{0}{1:d}'.format("O", incremental_feed))
            elif param in "XYZ":
                if param in state and state[param] == c.Parameters[param]:
                    continue
                else:
                    pos = toUM(c.Parameters[param])
                    outstring.append('{0}{1:d}'.format(param, pos))
            elif param in "T":
                tool = toNatural(c.Parameters[param])
                outstring.append('{1:d}'.format(param, tool))
            elif param in "S":
                speed = toNatural(c.Parameters[param])
                outstring.append('RPM {1:d}'.format(param, speed))
            else:
                # TODO
                # H tool length offset
                print("skipping unknown parameter {0} = {1}".format(param, c.Parameters[param]))

        # prepend a line number and append a newline
        if len(outstring) >= 1:
            if command == 'DRILLDEF':
                for option in outstring[1:]:
                    if option[0] in "XY":
                        continue # skip coordinates, they will be used in "G80/DRILL"
                    elif option[0] in "Z":
                        option = '{0}{1:d}'.format('D', toUM(-1 * c.Parameters['Z']))
                        out += linenumber() + COMMAND_SPACE.join(['DRILLDEF', option]) + '\n'
                    else:
                        out += linenumber() + COMMAND_SPACE.join(['DRILLDEF', option]) + '\n'
            elif command == 'DRILL':
                drillop = ['DRILL'] + ['{0}{1:d}'.format(p, toUM(state[p])) for p in "XY"]
                out += linenumber() + COMMAND_SPACE.join(drillop) + '\n'

            else:
                out += linenumber() + COMMAND_SPACE.join(outstring) + '\n'


        # update our state with the current position and state
        state.update({k: c.Parameters[k] for k in "XYZF" if k in c.Parameters})

    return out

print(__name__ + " gcode postprocessor loaded.")
