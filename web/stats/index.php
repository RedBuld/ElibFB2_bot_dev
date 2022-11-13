<?php
if(!isset($_GET['payload']) && !isset($_GET['bot_id']))
{
	die("There's nothing interesting");
}
$bot_id = '';
if(isset($_GET['bot_id']))
{
	$bot_id = $_GET['bot_id'];
}
else
{
	$payload = json_decode($_GET['payload'],true);
	$bot_id = $payload['bot'];
}
function plural_form($n, $forms)
{
	return $n.' '.($n%10==1&&$n%100!=11?$forms[0]:($n%10>=2&&$n%10<=4&&($n%100<10||$n%100>=20)?$forms[1]:$forms[2]));
}

$day = date("Y-m-d");
$day_prev = date("Y-m-d",strtotime("-1 days"));
$month = [date("Y-m-01"),date("Y-m-t")];
$month_prev = [date("Y-m-01",strtotime("-1 months")),date("Y-m-t",strtotime("-1 months"))];
function total_fsize($n)
{
	$n = intval($n);
	$t = "Кб";
	if($n > 10240)
	{
		$n = $n/1024;
		$t = "Мб";
	}
	if($n > 10240)
	{
		$n = $n/1024;
		$t = "Гб";
	}
	if($n > 10240)
	{
		$n = $n/1024;
		$t = "Тб";
	}
	$n = intval($n);
	return "{$n} {$t}";
}

$sql_day = "SELECT sites_stats.site, sites_stats.count, sites_stats.fsize FROM sites_stats WHERE sites_stats.day = '_DAY_' AND sites_stats.bot_id = '_BOT_' ORDER BY sites_stats.site ASC";
$sql_month = "SELECT sites_stats.site, sum(sites_stats.count) AS count, sum(sites_stats.fsize) AS fsize FROM sites_stats WHERE sites_stats.day BETWEEN '_START_' AND '_END_' AND sites_stats.bot_id = '_BOT_' GROUP BY sites_stats.site ORDER BY sites_stats.site ASC";
$sql_total = "SELECT sites_stats.site, sum(sites_stats.count) AS count, sum(sites_stats.fsize) AS fsize FROM sites_stats WHERE sites_stats.bot_id = '_BOT_' GROUP BY sites_stats.site ORDER BY sites_stats.site ASC";
$sql_total_all = "SELECT sites_stats.site, sum(sites_stats.count) AS count, sum(sites_stats.fsize) AS fsize FROM sites_stats GROUP BY sites_stats.site ORDER BY sites_stats.site ASC";

$w = ["скачивание","скачивания","скачиваний"];
$mysqli = new mysqli("localhost", "grampus-tg-bot-v2", "grampus-tg-bot-v2", "grampus-tg-bot-v2");
$sql_day = str_replace('_BOT_', $mysqli->real_escape_string($bot_id), $sql_day);
$sql_month = str_replace('_BOT_', $mysqli->real_escape_string($bot_id), $sql_month);
$sql_total = str_replace('_BOT_', $mysqli->real_escape_string($bot_id), $sql_total);

$hs = false;
?>
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<script src="https://telegram.org/js/telegram-web-app.js"></script>
	<link rel="stylesheet" href="app.css?v=<?=@filemtime(__DIR__.'/app.css')?>">
</head>
<body>
	<div id="download_stats">
		<?php
		$sql = str_replace('_DAY_', $day, $sql_day);
		$result = $mysqli->query($sql);
		$total = 0;
		$fsize = 0;

		if( $result->num_rows > 0 )
		{
			$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="3">Статистика за сегодня</th>
				</tr>
				<tr>
					<th>Сайт</th>
					<th>Скачиваний</th>
					<th>Объем</th>
				</tr>
			</thead>
			<tbody>
				<?php
				foreach( $result as $row )
				{
				?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
					<td><?=total_fsize($row['fsize'])?></td>
				</tr>
				<?php
				$total+=intval($row['count']);
				$fsize+=intval($row['fsize']);
				}
				?>
				<tr>
					<td>Всего</td>
					<td><?=plural_form($total,$w)?></td>
					<td><?=total_fsize($fsize)?></td>
				</tr>
			</tbody>
		</table>
		<?php
		}


		$sql = str_replace('_DAY_', $day_prev, $sql_day);
		$result = $mysqli->query($sql);
		$total = 0;
		$fsize = 0;

		if( $result->num_rows > 0 )
		{
			$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="3">Статистика за вчера</th>
				</tr>
				<tr>
					<th>Сайт</th>
					<th>Скачиваний</th>
					<th>Объем</th>
				</tr>
			</thead>
			<tbody>
				<?php
				foreach( $result as $row )
				{
				?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
					<td><?=total_fsize($row['fsize'])?></td>
				</tr>
				<?php
				$total+=intval($row['count']);
				$fsize+=intval($row['fsize']);
				}
				?>
				<tr>
					<td>Всего</td>
					<td><?=plural_form($total,$w)?></td>
					<td><?=total_fsize($fsize)?></td>
				</tr>
			</tbody>
		</table>
		<?php
		}

		$sql = str_replace('_START_', $month[0], $sql_month);
		$sql = str_replace('_END_', $month[1], $sql);
		$result = $mysqli->query($sql);
		$total = 0;
		$fsize = 0;

		if( $result->num_rows > 0 )
		{
			$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="3">Статистика за месяц</th>
				</tr>
				<tr>
					<th>Сайт</th>
					<th>Скачиваний</th>
					<th>Объем</th>
				</tr>
			</thead>
			<tbody>
				<?php
				foreach( $result as $row )
				{
				?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
					<td><?=total_fsize($row['fsize'])?></td>
				</tr>
				<?php
				$total+=intval($row['count']);
				$fsize+=intval($row['fsize']);
				}
				?>
				<tr>
					<td>Всего</td>
					<td><?=plural_form($total,$w)?></td>
					<td><?=total_fsize($fsize)?></td>
				</tr>
			</tbody>
		</table>
		<?php
		}

		$sql = str_replace('_START_', $month_prev[0], $sql_month);
		$sql = str_replace('_END_', $month_prev[1], $sql);
		$result = $mysqli->query($sql);
		$total = 0;
		$fsize = 0;

		if( $result->num_rows > 0 )
		{
			$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="3">Статистика за прошлый месяц</th>
				</tr>
				<tr>
					<th>Сайт</th>
					<th>Скачиваний</th>
					<th>Объем</th>
				</tr>
			</thead>
			<tbody>
				<?php
				foreach( $result as $row )
				{
				?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
					<td><?=total_fsize($row['fsize'])?></td>
				</tr>
				<?php
				$total+=intval($row['count']);
				$fsize+=intval($row['fsize']);
				}
				?>
				<tr>
					<td>Всего</td>
					<td><?=plural_form($total,$w)?></td>
					<td><?=total_fsize($fsize)?></td>
				</tr>
			</tbody>
		</table>
		<?php
		}

		/*

		$result = $mysqli->query($sql_total);
		$total = 0;
		$fsize = 0;

		if( $result->num_rows > 0 )
		{
			$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="3">Статистика всего</th>
				</tr>
				<tr>
					<th>Сайт</th>
					<th>Скачиваний</th>
					<th>Объем</th>
				</tr>
			</thead>
			<tbody>
				<?php
				foreach( $result as $row )
				{
				?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
					<td><?=total_fsize($row['fsize'])?></td>
				</tr>
				<?php
				$total+=intval($row['count']);
				$fsize+=intval($row['fsize']);
				}
				?>
				<tr>
					<td>Всего</td>
					<td><?=plural_form($total,$w)?></td>
					<td><?=total_fsize($fsize)?></td>
				</tr>
			</tbody>
		</table>
		<?php
		}

		$result = $mysqli->query($sql_total_all);
		$total = 0;
		$fsize = 0;

		if( $result->num_rows > 0 )
		{
			$hs = true;
		?>
		<table>
			<thead>
				<tr>
					<th colspan="3">Статистика всего (все боты)</th>
				</tr>
				<tr>
					<th>Сайт</th>
					<th>Скачиваний</th>
					<th>Объем</th>
				</tr>
			</thead>
			<tbody>
				<?php
				foreach( $result as $row )
				{
				?>
				<tr>
					<td><a target="_blank" href="http://<?=$row['site']?>"><?=$row['site']?></a></td>
					<td><?=plural_form($row['count'],$w)?></td>
					<td><?=total_fsize($row['fsize'])?></td>
				</tr>
				<?php
				$total+=intval($row['count']);
				$fsize+=intval($row['fsize']);
				}
				?>
				<tr>
					<td>Всего</td>
					<td><?=plural_form($total,$w)?></td>
					<td><?=total_fsize($fsize)?></td>
				</tr>
			</tbody>
		</table>
		<?php
		}

		*/

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