#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Basic functions, including timing, rush (imported), quit
"""
# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

import sys
import threading
import subprocess
import shlex
import locale

# some things are imported just to be accessible within core's namespace
from psychopy.clock import (MonotonicClock, Clock, CountdownTimer,
                            wait, monotonicClock, getAbsTime,
                            StaticPeriod)  # pylint: disable=W0611

# always safe to call rush, even if its not going to do anything for a
# particular OS
from psychopy.platform_specific import rush  # pylint: disable=W0611
from psychopy import logging
from psychopy.constants import STARTED, NOT_STARTED, FINISHED

try:
    import pyglet
    havePyglet = True
    # may not want to check, to preserve terminal window focus
    checkPygletDuringWait = True
except ImportError:
    havePyglet = False
    checkPygletDuringWait = False

try:
    import glfw
    haveGLFW = True
except ImportError:
    haveGLFW = False

runningThreads = []  # just for backwards compatibility?
openWindows = []  # visual.Window updates this, event.py and clock.py use it

# Set getTime in core to == the monotonicClock instance created in the
# clockModule.
# The logging module sets the defaultClock to == clock.monotonicClock,
# so by default the core.getTime() and logging.defaultClock.getTime()
# functions return the 'same' timebase.
#
# This way 'all' OSs have a core.getTime() timebase that starts at 0.0 when
# the experiment is launched, instead of it being this way on Windows only
# (which was also a descripancy between OS's when win32 was using time.clock).


def getTime(applyZero = True):
    """Get the current time since psychopy.core was loaded.



    Version Notes: Note that prior to PsychoPy 1.77.00 the behaviour of
    getTime() was platform dependent (on OSX and linux it was equivalent to
    :func:`psychopy.core.getAbsTime`
    whereas on windows it returned time since loading of the module, as now)
    """
    return monotonicClock.getTime(applyZero)


def quit():
    """Close everything and exit nicely (ending the experiment)
    """
    # pygame.quit()  # safe even if pygame was never initialised
    logging.flush()

    # properly shutdown ioHub server
    from psychopy.iohub.client import ioHubConnection

    if ioHubConnection.ACTIVE_CONNECTION:
        ioHubConnection.ACTIVE_CONNECTION.quit()

    for thisThread in threading.enumerate():
        if hasattr(thisThread, 'stop') and hasattr(thisThread, 'running'):
            # this is one of our event threads - kill it and wait for success
            thisThread.stop()
            while thisThread.running == 0:
                pass  # wait until it has properly finished polling

    sys.exit(0)  # quits the python session entirely


def shellCall(shellCmd, stdin='', stderr=False, env=None, encoding=None):
    """Call a single system command with arguments, return its stdout.
    Returns stdout, stderr if stderr is True.
    Handles simple pipes, passing stdin to shellCmd (pipes are untested
    on windows) can accept string or list as the first argument

    Parameters
    ----------
    shellCmd : str, or iterable
        The command to execute, and its respective arguments.

    stdin : str, or None
        Input to pass to the command.

    stderr : bool
        Whether to return the standard error output once execution is finished.

    env : dict
        The environment variables to set during execution.

    encoding : str
        The encoding to use for communication with the executed command.
        This argument will be ignored on Python 2.7.

    Notes
    -----
    We use ``subprocess.Popen`` to execute the command and establish
    `stdin` and `stdout` pipes.
    Python 2.7 always opens the pipes in text mode; however,
    Python 3 defaults to binary mode, unless an encoding is specified.
    To unify pipe communication across Python 2 and 3, we now provide an
    `encoding` parameter, enforcing `utf-8` text mode by default.
    This parameter is present from Python 3.6 onwards; using an older
    Python 3 version will raise an exception. The parameter will be ignored
    when running Python 2.7.

    """
    if encoding is None:
        encoding = locale.getpreferredencoding()

    if type(shellCmd) == str:
        # safely split into cmd+list-of-args, no pipes here
        shellCmdList = shlex.split(shellCmd)
    elif type(shellCmd) == bytes:
        # safely split into cmd+list-of-args, no pipes here
        shellCmdList = shlex.split(shellCmd.decode('utf-8'))
    elif type(shellCmd) in (list, tuple):  # handles whitespace in filenames
        shellCmdList = shellCmd
    else:
        msg = 'shellCmd requires a string or iterable.'
        raise TypeError(msg)

    cmdObjects = []
    for obj in shellCmdList:
        if type(obj) != bytes:
            cmdObjects.append(obj)
        else:
            cmdObjects.append(obj.decode('utf-8'))

    # the `encoding` parameter results in unicode coming back
    if sys.version_info.minor >= 6:
        proc = subprocess.Popen(cmdObjects, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                encoding=encoding, env=env)
    else:
        msg = 'shellCall() requires Python 2.7, or 3.6 and newer.'
        raise RuntimeError(msg)

    stdoutData, stderrData = proc.communicate(stdin)

    del proc
    if stderr:
        return stdoutData.strip(), stderrData.strip()
    else:
        return stdoutData.strip()


def getFromNames(names, namespace=None):
    """
    Get a component, or any other object handle, from a string containing its variable name.

    Parameters
    ==========
    names : str, list or tuple
        String representing the name of a variable, or a list/tuple (or listlike string) of names.
    namespace : dict or None
        dict mapping names to values, if None will use `globals()`
    """
    # If listlike string, split into list
    if isinstance(names, str) and "," in names:
        # Strip perentheses
        if (
                (names.startswith("[") and names.endswith("]"))
                or (names.startswith("(") and names.endswith(")"))
        ):
            names = names[1:-1]
        # Split at commas
        namesList = []
        for thisName in names.split(","):
            # Strip spaces
            thisName = thisName.strip()
            # Strip quotes
            if (
                    (thisName.startswith('"') and thisName.endswith('"'))
                    or (thisName.startswith("'") and thisName.endswith("'"))
            ):
                thisName = thisName[1:-1]
            # Append
            namesList.append(thisName)
        names = namesList

    # If single name, put in list
    from collections.abc import Iterable
    if isinstance(names, str) or not isinstance(names, Iterable):
        names = [names]

    # Get objects
    objs = []
    for nm in names:
        # Get from globals if no namespace
        if namespace is None:
            namespace = globals()
        # Get (use original value if not present)
        obj = namespace.get(nm, nm)
        # Append
        objs.append(obj)

    return objs


def setExecEnvironment(env):
    # Get builtin exec function
    import builtins
    # Create new exec function in given environment
    def exec(call_str):
        builtins.exec(call_str, env)
    exec.__doc__ = builtins.exec.__doc__
    # Return function
    return exec


class ComponentPlaceholder:
    """
    When a component is not implemented, we need an object to represent it when running, which will accept any
    attribute given without causing an error and breaking the experiment. This object extends the base Python
    `object` class, with no additions.
    """
    pass
