<?php
$bot_id = $_GET['bot_id'];

$botnames = array(
	'c1' => 'Chat c1',
	'b1' => 'Books b1',
	'r1' => 'Ranobe r1',
	'm1' => 'Manga m1',
	'j1' => 'Jaomix j1',
	'wx1' => 'Wuxia wx1',
);

$mysqli = new mysqli("localhost", "grampus-tg-bot-v2", "grampus-tg-bot-v2", "grampus-tg-bot-v2");

$result = $mysqli->query("SELECT * FROM `bots_stats`");

$stats = array();
foreach( $result as $row )
{
	$stats[ $row['bot_id'] ] = array(
		'queue_length' => $row['queue_length'],
		'queue_limit' => $row['queue_limit'],
		'queue_act' => $row['queue_act'],
		'queue_sim' => $row['queue_sim'],
		'last_on' => $row['last_on'],
	);
}

?>
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<script src="https://telegram.org/js/telegram-web-app.js"></script>
	<script src="app.js?v=<?=@filemtime(__DIR__.'/app.js')?>" defer></script>
	<link rel="stylesheet" href="app.css?v=<?=@filemtime(__DIR__.'/app.css')?>">
</head>
<body>
	<div id="bot_stats">
		<table>
			<thead>
				<tr>
					<th>Бот</th>
					<th width="35%">Длина очереди</th>
					<th width="35%">Загрузка очереди</th>
				</tr>
			</thead>
			<tbody>
				<?php
				foreach( $botnames as $botid => $botname )
				{
				?>
				<tr class="<?=($bot_id==$botid?'current':'')?>">
					<td><?=$botname?></td>
					<td>
						<div class="progressbar">
							<div class="bar" style="width:<?=( $stats[ $botid ]['queue_length'] / $stats[ $botid ]['queue_limit'] * 100 )?>%"></div>
						</div>
					</td>
					<td>
						<div class="progressbar">
							<div class="bar" style="width:<?=( $stats[ $botid ]['queue_act'] / $stats[ $botid ]['queue_sim'] * 100 )?>%"></div>
						</div>
					</td>
				</tr>
				<?php
				}
				?>
			</tbody>
		</table>
	</div>
</body>
</html>