#!/usr/bin/env python
# -*- coding: utf-8 -*-



from pathlib import Path
from psychopy.experiment.components import BaseComponent, Param, _translate
from psychopy.localization import _localized as __localized
_localized = __localized.copy()

# only use _localized values for label values, nothing functional:
_localized.update({'forceEndRoutineOnPress': _translate('End Routine on press'),
                   'timeRelativeTo': _translate('Time relative to'),
                   'lights': _translate('Button lights'),
                   'clickable': _translate('Clickable buttons')})


class ButtonboxComponent(BaseComponent):
    """An event class for checking the mouse location and buttons
    at given timepoints
    """
    categories = ['Responses']
    targets = ['PsychoPy']
    iconFile = Path(__file__).parent / 'mouse.png'
    tooltip = _translate('Buttonbox: Record Responsepixx buttonpresses')

    def __init__(self, exp, parentName, name='buttonbox',
                 startType='time (s)', startVal=0.0,
                 stopType='duration (s)', stopVal=1.0,
                 startEstim='', durationEstim='',
                 save='on click', forceEndRoutineOnPress="any click",
                 lights=True,
                 clickable=['red','green','yellow','blue','white'],
                 timeRelativeTo='buttonbox onset'):
        super(ButtonboxComponent, self).__init__(
            exp, parentName, name=name,
            startType=startType, startVal=startVal,
            stopType=stopType, stopVal=stopVal,
            startEstim=startEstim, durationEstim=durationEstim)

        self.type = 'Buttonbox'
        self.url = ""

        self.order += [
            'forceEndRoutineOnPress', 'lights', 'clickable',  # Basic tab
            'timeRelativeTo',  # Data tab
            ]

        # params

        msg = _translate("Should a button press force the end of the routine"
                         " (e.g end the trial)?")
        if forceEndRoutineOnPress is True:
            forceEndRoutineOnPress = 'any click'
        elif forceEndRoutineOnPress is False:
            forceEndRoutineOnPress = 'never'
        self.params['forceEndRoutineOnPress'] = Param(
            forceEndRoutineOnPress, valType='str', inputType="choice", categ='Basic',
            allowedVals=['never', 'any click', 'valid click', 'correct click'],
            updates='constant', direct=False,
            hint=msg,
            label=_localized['forceEndRoutineOnPress'])
        
        msg = _translate("Should the button lights be turned on?")
        
        self.params['lights'] = Param(
            True, valType='bool', inputType="bool", categ='Basic',
            updates='constant',
            hint=msg,
            label=_localized['lights'])

        msg = _translate("What should the values of buttonbox.time be "
                         "relative to?")
        self.params['timeRelativeTo'] = Param(
            timeRelativeTo, valType='str', inputType="choice", categ='Data',
            allowedVals=['buttonbox onset', 'experiment', 'routine'],
            updates='constant',
            hint=msg, direct=False,
            label=_localized['timeRelativeTo'])
        
        msg = _translate('A comma-separated list of the buttons (colors) '
                         'that can be clicked.')
        self.params['clickable'] = Param(
            '', valType='list', inputType="single", categ='Basic',
            updates='constant',
            hint=msg,
            label=_localized['clickable'])

    @property
    def writeInitCode(self, buff):
        code = ("#initialize buttonbox"
                "from psychopy_pixx.devices import Responsepixx"
                "%(name)s = ResponsePixx(pixxdevice, buttons = buttons, events = [\'down\'], lights = lights"
                "%(name)s.buttonboxClock = core.Clock()\n")
        buff.writeIndentedLines(code % self.params)

    def writeRoutineStartCode(self, buff):
        """Write the code that will be called at the start of the routine
        """
        # create some lists to store recorded values positions and events if
        # we need more than one
        code = ("# starting the buttonbox and setup a python list for storing the button presses of "
                "%(name)s\n"
                "%(name)s.start()\n"
                "(name)sResp = []\n")

        if self.params['timeRelativeTo'].val.lower() == 'routine':
            code += "%(name)s.buttonboxClock.reset()\n"

        buff.writeIndentedLines(code % self.params)

    def writeFrameCode(self, buff):
        """Write the code that will be called every frame"""

        forceEnd = self.params['forceEndRoutineOnPress'].val

        # get a clock for timing
        timeRelative = self.params['timeRelativeTo'].val.lower()
        if timeRelative == 'experiment':
            self.clockStr = 'globalClock'
        elif timeRelative in ['routine', 'buttonbox onset']:
            self.clockStr = '%s.buttonboxClock' % self.params['name'].val

        buff.writeIndented("# *%s* updates\n" % self.params['name'])

        # writes an if statement to determine whether to draw etc
        indented = self.writeStartTestCode(buff)
        if indented:
            code = ""
            if self.params['timeRelativeTo'].val.lower() == 'buttonbox onset':
                code += "%(name)s.buttonboxClock.reset()\n"

            if self.params['newClicksOnly']:
                code += (
                    "prevButtonState = %(name)s.getKeys()"
                    "  # if button is down already this ISN'T a new click\n")
            else:
                code += (
                    "prevButtonState = []"
                    "  # if now button is down we will treat as 'new' click\n")
            buff.writeIndentedLines(code % self.params)

        # to get out of the if statement
        buff.setIndentLevel(-indented, relative=True)

        # test for stop (only if there was some setting for duration or stop)
        indented = self.writeStopTestCode(buff)
        # to get out of the if statement
        buff.setIndentLevel(-indented, relative=True)

        # only write code for cases where we are storing data as we go (each
        # frame or each click)

        # if STARTED and not FINISHED!
        code = ("if %(name)s.status == STARTED:  "
                "# only update if started and not finished!\n") % self.params
        buff.writeIndented(code)
        buff.setIndentLevel(1, relative=True)  # to get out of if statement
        dedentAtEnd = 1  # keep track of how far to dedent later

        def _buttonPressCode(buff, dedent):
            """Code compiler for mouse button events"""
            code = ("buttons = %(name)s.getKeys()\n"
                    "if buttons != prevButtonState:  # button state changed?")
            buff.writeIndentedLines(code % self.params)
            buff.setIndentLevel(1, relative=True)
            dedent += 1
            buff.writeIndented("prevButtonState = buttons\n")
            code = ("if buttons > 0:  # state changed to a new click\n"
                    "lastResp = buttons[-1]")
            buff.writeIndentedLines(code % self.params)
            buff.setIndentLevel(1, relative=True)
            dedent += 1
            return buff, dedent

        # No mouse tracking, end routine on any or valid click
        if self.params['saveMouseState'].val in ['never', 'final'] and forceEnd != "never":
            buff, dedentAtEnd = _buttonPressCode(buff, dedentAtEnd)

            if forceEnd == 'valid click':
                    # does valid response end the trial?
                    code = ("if gotValidClick:  \n"
                            "    continueRoutine = False  # end routine on response\n")
                    buff.writeIndentedLines(code)
                    buff.setIndentLevel(-dedentAtEnd, relative=True)
            else:
                buff.writeIndented('continueRoutine = False  # end routine on response')
                buff.setIndentLevel(-dedentAtEnd, relative=True)

        elif self.params['saveMouseState'].val != 'never':
            mouseCode = ("x, y = {name}.getPos()\n"
                    "{name}.x.append(x)\n"
                    "{name}.y.append(y)\n"
                    "buttons = {name}.getPressed()\n"
                    "{name}.leftButton.append(buttons[0])\n"
                    "{name}.midButton.append(buttons[1])\n"
                    "{name}.rightButton.append(buttons[2])\n"
                    "{name}.time.append({clockStr}.getTime())\n".format(name=self.params['name'],
                                                                        clockStr=self.clockStr))

            # Continuous mouse tracking
            if self.params['saveMouseState'].val in ['every frame']:
                buff.writeIndentedLines(mouseCode)

            # Continuous mouse tracking for all button press
            if forceEnd == 'never' and self.params['saveMouseState'].val in ['on click', 'on valid click']:
                buff, dedentAtEnd = _buttonPressCode(buff, dedentAtEnd)
                if self.params['saveMouseState'].val in ['on click']:
                    buff.writeIndentedLines(mouseCode)
                elif self.params['clickable'].val and self.params['saveMouseState'].val in ['on valid click']:
                    code = (
                        "if gotValidClick:\n"
                    )
                    buff.writeIndentedLines(code)
                    buff.setIndentLevel(+1, relative=True)
                    buff.writeIndentedLines(mouseCode)
                    buff.setIndentLevel(-1, relative=True)

            # Mouse tracking for events that end routine
            elif forceEnd != "never":
                buff, dedentAtEnd = _buttonPressCode(buff, dedentAtEnd)
                # Save all mouse events on button press
                if self.params['saveMouseState'].val in ['on click']:
                    buff.writeIndentedLines(mouseCode)
                elif self.params['clickable'].val and self.params['saveMouseState'].val in ['on valid click']:
                    code = (
                        "if gotValidClick:\n"
                    )
                    buff.writeIndentedLines(code)
                    buff.setIndentLevel(+1, relative=True)
                    buff.writeIndentedLines(mouseCode)
                    buff.setIndentLevel(-1, relative=True)
                # also write code about clicked objects if needed.
                if self.params['clickable'].val:
                    # does valid response end the trial?
                    if forceEnd == 'valid click':
                        code = ("if gotValidClick:\n"
                                "    continueRoutine = False  # end routine on response\n")
                        buff.writeIndentedLines(code)
                # does any response end the trial?
                if forceEnd == 'any click':
                    code = ("\n"
                            "continueRoutine = False  # end routine on response\n")
                    buff.writeIndentedLines(code)
                elif forceEnd == 'correct click':
                    code = (
                        "if %(name)s.corr and %(name)s.corr[-1]:\n"
                        "    continueRoutine = False  # end routine on response\n"
                    )
                else:
                    pass # forceEnd == 'never'
                # 'if' statement of the time test and button check
            buff.setIndentLevel(-dedentAtEnd, relative=True)


    def writeRoutineEndCode(self, buff):
        # some shortcuts
        name = self.params['name']
        # do this because the param itself is not a string!
        store = self.params['saveMouseState'].val
        if store == 'nothing':
            return

        forceEnd = self.params['forceEndRoutineOnPress'].val
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler

        if currLoop.type == 'StairHandler':
            code = ("# NB PsychoPy doesn't handle a 'correct answer' for "
                    "mouse events so doesn't know how to handle mouse with "
                    "StairHandler\n")
        else:
            code = ("# store data for %s (%s)\n" %
                    (currLoop.params['name'], currLoop.type))

        buff.writeIndentedLines(code)

        if store == 'final':  # for the o
            # buff.writeIndented("# get info about the %(name)s\n"
            # %(self.params))
            code = ("x, y = {name}.getPos()\n"
                    "buttons = {name}.getPressed()\n").format(name=self.params['name'])
            # also write code about clicked objects if needed.
            buff.writeIndentedLines(code)
            if self.params['clickable'].val:
                buff.writeIndented("if sum(buttons):\n")
                buff.setIndentLevel(+1, relative=True)
                self._writeClickableObjectsCode(buff)
                buff.setIndentLevel(-1, relative=True)

            if currLoop.type != 'StairHandler':
                code = (
                    "{loopName}.addData('{name}.x', x)\n" 
                    "{loopName}.addData('{name}.y', y)\n" 
                    "{loopName}.addData('{name}.leftButton', buttons[0])\n" 
                    "{loopName}.addData('{name}.midButton', buttons[1])\n" 
                    "{loopName}.addData('{name}.rightButton', buttons[2])\n"
                )
                if self.params['storeCorrect']:
                    code += (
                        "{loopName}.addData('{name}.corr', {name}.corr)\n"
                    )
                buff.writeIndentedLines(
                    code.format(loopName=currLoop.params['name'],
                                name=name))
                # then add `trials.addData('mouse.clicked_name',.....)`
                if self.params['clickable'].val:
                    for paramName in self._clickableParamsList:
                        code = (
                            "if len({name}.clicked_{param}):\n"
                            "    {loopName}.addData('{name}.clicked_{param}', " 
                            "{name}.clicked_{param}[0])\n"
                        )
                        buff.writeIndentedLines(
                            code.format(loopName=currLoop.params['name'],
                                        name=name,
                                        param=paramName))

        elif store != 'never':
            # buff.writeIndented("# save %(name)s data\n" %(self.params))
            mouseDataProps = ['x', 'y', 'leftButton', 'midButton',
                             'rightButton', 'time']
            if self.params['storeCorrect']:
                mouseDataProps += ['corr']
            # possibly add clicked params if we have clickable objects
            if self.params['clickable'].val:
                for paramName in self._clickableParamsList:
                    mouseDataProps.append("clicked_{}".format(paramName))
            # use that set of properties to create set of addData commands
            for property in mouseDataProps:
                if store == 'every frame' or forceEnd == "never":
                    code = ("%s.addData('%s.%s', %s.%s)\n" %
                            (currLoop.params['name'], name,
                             property, name, property))
                    buff.writeIndented(code)
                else:
                    # we only had one click so don't return a list
                    code = ("%s.addData('%s.%s', %s.%s)\n" %
                            (currLoop.params['name'], name,
                             property, name, property))
                    buff.writeIndented(code)


        # get parent to write code too (e.g. store onset/offset times)
        super().writeRoutineEndCode(buff)

        if currLoop.params['name'].val == self.exp._expHandler.name:
            buff.writeIndented("%s.nextEntry()\n" % self.exp._expHandler.name)