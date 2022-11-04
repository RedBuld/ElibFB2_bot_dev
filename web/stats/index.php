<?php
$payload = json_decode($_GET['payload'],true);
function plural_form($n, $forms)
{
	return $n.' '.($n%10==1&&$n%100!=11?$forms[0]:($n%10>=2&&$n%10<=4&&($n%100<10||$n%100>=20)?$forms[1]:$forms[2]));
}

$sql_day = "SELECT sites_stats.site, sites_stats.count FROM sites_stats WHERE sites_stats.day = '_DAY_' AND sites_stats.bot_id = '_BOT_' ORDER BY sites_stats.site ASC";
$sql_month = "SELECT sites_stats.site, sum(sites_stats.count) AS count FROM sites_stats WHERE sites_stats.day BETWEEN '_START_' AND '_END_' AND sites_stats.bot_id = '_BOT_' GROUP BY sites_stats.site ORDER BY sites_stats.site ASC";

$w = ["скачивание","скачивания","скачиваний"];
$mysqli = new mysqli("localhost", "grampus-tg-bot-v2", "grampus-tg-bot-v2", "grampus-tg-bot-v2");
$sql_day = str_replace('_BOT_', $mysqli->real_escape_string($payload['bot']), $sql_day);
$sql_month = str_replace('_BOT_', $mysqli->real_escape_string($payload['bot']), $sql_month);

$hs = false;
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
	<div id="download_stats">
		<?php
		if( array_key_exists('sql_daily', $payload) )
		{
			$sql = str_replace('_DAY_', $mysqli->real_escape_string($payload['sql_daily']), $sql_day);
			$result = $mysqli->query($sql);

			if( $result->num_rows > 0 )
			{
				$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="2">Статистика за сегодня</th>
				</tr>
			</thead>
			<tbody>
				<?php foreach( $result as $row ) { ?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
				</tr>
				<?php } ?>
			</tbody>
		</table>
		<?php
			}
		}

		if( array_key_exists('sql_daily_prev', $payload) )
		{
			$sql = str_replace('_DAY_', $mysqli->real_escape_string($payload['sql_daily_prev']), $sql_day);
			$result = $mysqli->query($sql);

			if( $result->num_rows > 0 )
			{
				$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="2">Статистика за вчера</th>
				</tr>
			</thead>
			<tbody>
				<?php foreach( $result as $row ) { ?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
				</tr>
				<?php } ?>
			</tbody>
		</table>
		<?php
			}
		}

		if( array_key_exists('sql_montly', $payload) )
		{
			$sql = str_replace('_START_', $mysqli->real_escape_string($payload['sql_montly'][0]), $sql_month);
			$sql = str_replace('_END_', $mysqli->real_escape_string($payload['sql_montly'][1]), $sql);
			$result = $mysqli->query($sql);
			if( $result->num_rows > 0 )
			{
				$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="2">Статистика за месяц</th>
				</tr>
			</thead>
			<tbody>
				<?php foreach( $result as $row ) { ?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
				</tr>
				<?php } ?>
			</tbody>
		</table>
		<?php
			}
		}

		if( array_key_exists('sql_montly_prev', $payload) )
		{
			$sql = str_replace('_START_', $mysqli->real_escape_string($payload['sql_montly_prev'][0]), $sql_month);
			$sql = str_replace('_END_', $mysqli->real_escape_string($payload['sql_montly_prev'][1]), $sql);
			$result = $mysqli->query($sql);
			if( $result->num_rows > 0 )
			{
				$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="2">Статистика за прошлый месяц</th>
				</tr>
			</thead>
			<tbody>
				<?php foreach( $result as $row ) { ?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
				</tr>
				<?php } ?>
			</tbody>
		</table>
		<?php
			}
		}

		if(!$hs)
		{
		?>
		<h2>Пока статистики нет</h2>
		<?php
		}
		?>
	</div>
</body>
</html>