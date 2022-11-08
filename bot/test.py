import asyncio

async def test():

	log = open('/usr/share/tg-bot-v2/instance/downloader/logs/m1-470328529-712.log', 'w')
	_process = await asyncio.create_subprocess_exec('dotnet','Elib2Ebook.dll','--save','"/usr/share/tg-bot-v2/instance/downloader/temp/m1-470328529-712"','--url','https://manga.ovh/chapter/533af571-f0f2-4260-98ee-55d32e780707','--format','cbz,json','--end','5','--timeout','30',stdout=log,cwd='/usr/share/tg-bot-v2/instance/downloader')
	print('sub',_process.pid)
	await _process.wait()

	# asyncio.sleep(5)
	# _process.kill()

async def test2():

	log = open('/usr/share/tg-bot-v2/instance/downloader/logs/m1-470328529-712.log', 'w')
	_process = await asyncio.create_subprocess_shell('cd /usr/share/tg-bot-v2/instance/downloader; dotnet Elib2Ebook.dll --save "/usr/share/tg-bot-v2/instance/downloader/temp/m1-470328529-712" --url "https://manga.ovh/chapter/533af571-f0f2-4260-98ee-55d32e780707" --format "cbz,json" --end 5 --timeout 30 > /usr/share/tg-bot-v2/instance/downloader/logs/m1-470328529-712.log')
	print('sub',_process.pid)
	await _process.wait()

	# asyncio.sleep(5)
	# _process.kill()

asyncio.run( test() )
# asyncio.run( test2() )