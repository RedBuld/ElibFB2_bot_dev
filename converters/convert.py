import argparse, asyncio, os

parser = argparse.ArgumentParser(prog='bot.py', conflict_handler='resolve')
parser.add_argument('source_folder', type=str, help='source folder')
parser.add_argument('target_folder', type=str, help='target folder')
parser.add_argument('target_format', type=str, help='target format')
execute_args = parser.parse_args()

_fb2c_formats = ['mobi','azw3']

async def _fb2c_covert(target_format,source_folder,target_folder):
	_exec = '_fb2c/fb2c'
	command = []
	command.append('convert')
	command.append('--nodirs')
	command.append('--to')
	command.append(target_format)
	command.append(source_folder)
	command.append(target_folder)

	_process = await asyncio.create_subprocess_exec(_exec, *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=os.path.dirname(os.path.abspath(__file__)))
	await _process.wait()


if execute_args.target_format in _fb2c_formats:
	asyncio.run( _fb2c_covert(execute_args.target_format,execute_args.source_folder,execute_args.target_folder) )