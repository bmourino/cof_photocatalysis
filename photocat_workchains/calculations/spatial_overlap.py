from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import RemoteData, Float

class OvlpCalculation(CalcJob):
    """AiiDA calculation plugin wrapping the MOFVacLevel executable."""
    _DEFAULT_INPUT_FILE = "ovlp.py"
    _DEFAULT_OUTPUT_FILE = "log.out"
    _DEFAULT_PARENT_CALC_FLDR_NAME = "parent_calc/"
    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        super(OvlpCalculation, cls).define(spec)

        # new ports
        spec.input('folder', valid_type=RemoteData, required=True, help='Folder where the calculation will be performed.')
        spec.input('epath', valid_type=RemoteData, required=True, help='Path to the folder of the electron injection calculation.')
        spec.input('hpath', valid_type=RemoteData, required=True, help='Path to the folder of the hole injection calculation.')
        spec.output('overlap', valid_type=Float, help='Computed averaged spatial overlap with cubes tools from https://github.com/kjappelbaum/cubes.')

        spec.input('metadata.options.output_filename', valid_type=str, default='log.out' )
        spec.inputs['metadata']['options']['resources'].default = {
                                            'num_machines': 1,
                                            'num_mpiprocs_per_machine': 1,
                                            }
        spec.inputs['metadata']['options']['parser_name'].default = 'photocat_workchains.overlap_parser'
        spec.exit_code(
            200,
            "ERROR_NO_RETRIEVED_FOLDER",
            message="The retrieved folder data node could not be accessed.",
        )
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES',
                message='Calculation did not produce all expected output files.')
        spec.exit_code(
            301, "ERROR_OUTPUT_READ", message="The output file could not be read."
        )
        spec.exit_code(
            302, "ERROR_OUTPUT_PARSE", message="The output file could not be parsed."
        )


    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files needed by
            the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        a = "'" + self.inputs.hpath.get_remote_path() + "'"
        b = "'" + self.inputs.epath.get_remote_path() + "'"

        lines = [f'hfolder = {a}\n',f'efolder = {b}\n'] 
        
        with open("/home/beatriz/aiida1.6/aiida_photocat/photocat_workchains/calculations/base/ovlp_base.py") as file:
            for line in file:
                lines.append(line.rstrip() + "\n")


        with folder.open("ovlp.py", 'w') as fobj:
            for i in lines:
                fobj.write(i)    




        codeinfo = datastructures.CodeInfo()
        codeinfo.cmdline_params = [self._DEFAULT_INPUT_FILE]
        codeinfo.stin_name = self._DEFAULT_INPUT_FILE
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self._DEFAULT_OUTPUT_FILE

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = datastructures.CalcInfo()
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._DEFAULT_INPUT_FILE
        calcinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        
        calcinfo.codes_info = [codeinfo]
        #calcinfo.local_copy_list = [
        #    (self.inputs.folder.uuid, self.inputs.folder.filename, self.inputs.folder.filename)
        #]
        calcinfo.retrieve_list = [self.metadata.options.output_filename]
        
        #Make a link of cube_file folder 
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        
        comp_uuid = self.inputs.folder.computer.uuid
        remote_path = self.inputs.folder.get_remote_path()
        copy_info = (comp_uuid, remote_path, self._DEFAULT_PARENT_CALC_FLDR_NAME)
        # If running on the same computer - make a symlink.
        if self.inputs.code.computer.uuid == comp_uuid:
            calcinfo.remote_symlink_list.append(copy_info)
        # If not - copy the folder.
        else:
            calcinfo.remote_copy_list.append(copy_info)

        return calcinfo


