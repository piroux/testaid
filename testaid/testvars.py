import json
import os
import re


class Testvars(object):

    def __init__(self, host):
        self.host = host
        self.testvars = {}

        # try to use ephemeral molecule directory to store unresolved testvars
        try:
            tempdir = os.environ['MOLECULE_EPHEMERAL_DIRECTORY']
        except:
            tempdir = '/tmp'

        # create json file for unresolved testvars
        self.testvars_dumpfilename = tempdir + '/testvars_unresolved.json'
        testvars_dumpfile = open(self.testvars_dumpfilename, 'w')

        # get variables from defaults/main.yml file of all roles
        testvars_unresolved = self. _include_roles_variables_('defaults')

        # respect variable precedence by updating variables with
        # global ansible variables provided by testinfra ansible module
        testvars_unresolved.update(self.host.ansible.get_variables())

        # get variables from all files in vars directory of project
        testvars_unresolved.update(self. _include_project_vars_('vars'))

        # get variables from vars/main.yml file of all roles
        testvars_unresolved.update(self. _include_roles_variables_('vars'))

        # convert unresolved test vars to json in order
        # to replace the templated variables through a regular exrpression
        self.testvars_unresolved_json = json.dumps(testvars_unresolved)

        # store unresolved testvars as json in a file as input to
        # the ansible debug module via command line --extra-vars
        testvars_dumpfile.write(self.testvars_unresolved_json)
        testvars_dumpfile.close()

        # resolve jinja2 templates by leveraging the ansible debug
        # module through the testinfra ansible module
        self._resolve_vars_()

    def _get_project_dir_(self):

        # use the molecule scenario directory as a starting point
        try:
            path = os.environ['MOLECULE_SCENARIO_DIRECTORY']
        except:
            return None

        # move up until we find a roles directory
        while path != '/':
            path = os.path.dirname(path)
            if 'roles' in os.listdir(path):
                return path

        return None

    def _include_roles_variables_(self, path):
        # filenames of the yml files
        roles_variables = {}

        # get roles dir starting at the molecule scenario directory
        roles_dir = self._get_project_dir_() + '/roles'

        if roles_dir:

            # get roles as subdirectories of the role directory
            roles = next(os.walk(roles_dir))[1]

            for role in roles:

                # build target path
                filepath_role_variables = os.path.join(
                    roles_dir,
                    role,
                    path,
                    'main.yml')

                if os.path.isfile(filepath_role_variables):

                    # use ansible include_vars module to read role variables
                    role_defaults = self.host.ansible(
                        "include_vars",
                        "file=" + filepath_role_variables)['ansible_facts']

                    # the variables of each role should be prefixed with the
                    # role name to avoid collisions
                    roles_variables.update(role_defaults)

        return roles_variables

    def _include_project_vars_(self, path):

        # filenames of the yml files
        vars_variables = {}

        # get vars dir starting at the molecule scenario directory
        vars_dir = self._get_project_dir_() + '/vars'

        if vars_dir:

            # loop over files in vars directory
            for vars_file in os.listdir(vars_dir):

                # only care about .yml files
                if vars_file.endswith(".yml"):

                    filepath_vars_file = os.path.join(vars_dir, vars_file)

                    # use ansible include_vars module to read role variables
                    vars_file_variables = self.host.ansible(
                        "include_vars",
                        "file=" + filepath_vars_file)['ansible_facts']

                    # the variables of each role should be prefixed with the
                    # role name to avoid collisions
                    vars_variables.update(vars_file_variables)

        return vars_variables

    def _resolve_vars_(self):

        # resolve templates
        regex_templates = r'{{.*?}}'
        testvars_json = \
            re.sub(regex_templates,
                   lambda match: self._resolve_template_(match.group(0)),
                   self.testvars_unresolved_json,
                   flags=re.S)

        # load json and unescape characters
        self.testvars = json.loads(testvars_json)

    def _resolve_template_(self, template_unresolved):

        # prepare arguments variable to pass
        # dumped testvars to ansible debug module
        kwargs = {'extravars': '--extra-vars=@' + self.testvars_dumpfilename}

        # use ansible debug module to resolve template
        template_resolved = str(self.host.ansible('debug', 'msg=' + template_unresolved, **kwargs)['msg'])

        # escape resolved template
        template_resolved = json.dumps(template_resolved).strip('"')

        return template_resolved
