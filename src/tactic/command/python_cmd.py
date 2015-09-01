###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#
__all__ = ['PythonCmd', 'PythonTrigger']

import tacticenv

from pyasm.common import TacticException, Environment, Config, jsondumps, jsonloads
from pyasm.command import Command, CommandExitException, Trigger
from pyasm.biz import Project
from pyasm.search import Search
from tactic_client_lib import TacticServerStub

from mako.template import Template
from mako import exceptions

import os

class PythonCmd(Command):

    def get_results(my):
        code = my.kwargs.get("code")
        script_path = my.kwargs.get("script_path")
        file_path = my.kwargs.get("file_path")


        # if a script path is specified, then get it from the custom_script
        # table
        if script_path:

            folder = os.path.dirname(script_path)
            title = os.path.basename(script_path)

            search = Search("config/custom_script")
            search.add_filter("folder", folder)
            search.add_filter("title", title)
            custom_script = search.get_sobject()
            if not custom_script:
                raise TacticException("Custom script with path [%s/%s] does not exist" % (folder, title) )
            code = custom_script.get_value("script")

        elif file_path:
            f = open(file_path)
            code = f.read()
            f.close()


        server = TacticServerStub.get(protocol='local')
        server.login = Environment.get_user_name()
        spt_mako_results = {}

        #kwargs = {
        #    'server': server,
        #    'spt_mako_results': spt_mako_results
        #}

        code = '''
<%%def name='spt_run_code()'>
<%%
%s
%%>
</%%def>

<%%
spt_mako_results['spt_ret_val'] = spt_run_code()
%%>
''' % code
        

        #template = Template(code, output_encoding='utf-8', input_encoding='utf-8')
        try:
            template = Template(code)
            template.render(server=server,spt_mako_results=spt_mako_results, kwargs=my.kwargs,**my.kwargs)
        except Exception, e:
            print "Error in Mako code: "
            print exceptions.text_error_template().render()
            print "---"
            print "Code:"
            print code
            print "---"
            raise
            raise CommandExitException(e)

        return spt_mako_results['spt_ret_val']



    def execute(my):

        code = my.kwargs.get("code")
        script_path = my.kwargs.get("script_path")
        file_path = my.kwargs.get("file_path")
        assert code or script_path or file_path

        results = my.get_results()

        # set info and description
        my.info['spt_ret_val'] = results 
        class_name = my.__class__.__name__
        if script_path:
            desc = 'Run %s with script path [%s]' % (class_name, script_path)
        else:
            desc = "Run %s with explicit code" % class_name
        my.add_description(desc)

        return results




class PythonTrigger(Trigger):

    def __init__(my, **kwargs):
        super(PythonTrigger,my).__init__()
        my.kwargs = kwargs
        my.ret_val = None
        my.script_path = my.kwargs.get("script_path")


    def set_script_path(my, script_path):
        my.script_path = script_path

    def get_title(my):
        return my.script_path

    def get_ret_val(my):
        return my.ret_val


    def execute(my):
        dirname = os.path.dirname(my.script_path)
        basename = os.path.basename(my.script_path)

        project = Project.get()

        # treat the code as a python
        search = Search("config/custom_script")
        search.add_filter("folder", dirname)
        search.add_filter("title", basename)
        script_sobj = search.get_sobject()

        if not script_sobj:
            try:
                # get from the sthpw database
                search = Search("sthpw/custom_script")
                search.add_filter("folder", dirname)
                search.add_filter("title", basename)
                script_sobj = search.get_sobject()
                if not script_sobj:
                    print("WARNING: Script with path [%s] does not exist in this project [%s] or Admin Site" % (my.script_path, project.get_code()))
                    return {}
            except:
                print("WARNING: Script with path [%s] does not exist in this project [%s] or Admin Site" % (my.script_path, project.get_code()))
                return

        script = script_sobj.get_value("script")
        if not script:
            print("WARNING: Empty python script [%s]" %script_sobj.get_code())
            return {}



        if my.trigger_sobj:
            trigger_sobj = my.trigger_sobj.get_sobject_dict()
            my.input['trigger_sobject'] = trigger_sobj

        language = script_sobj.get_value("language")
        if language == "server_js":
            from tactic.command import JsCmd
            cmd = JsCmd(code=script, input=my.input)
        else:
            cmd = PythonCmd(code=script, input=my.input)

        ret_val = cmd.execute()

        my.ret_val = ret_val

        #print "input: ", my.input
        #print "output: ", my.output
        #print "options: ", my.options

        return ret_val






# main program
if __name__ == '__main__':
    from pyasm.security import Batch
    Batch(project_code='sample3d')

    import time
    start = time.time()
    cmd = PythonCmd(script_path='trigger/note')
    
    cmd.execute()
    print time.time() - start









