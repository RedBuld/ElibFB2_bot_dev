<?php
if(!isset($_GET['payload']))
{
	die("There's nothing interesting");
}
$payload = json_decode($_GET['payload'],true);
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
	<form id="download_config">
		<?php if( isset( $payload['use_start'] ) && $payload['use_start'] ) { ?>
		<div class="form-row">
			<input class="input" type="number" id="start" name="start" inputmode="numeric" placeholder=" ">
			<label for="start" class="label">Скачивать с главы</label>
		</div>
		<p class="form-row-description"><em>Порядковый номер главы</em></p>
		<?php } ?>
		<?php if( isset( $payload['use_end'] ) && $payload['use_end'] ) { ?>
		<div class="form-row">
			<input class="input" type="number" id="end" name="end" inputmode="numeric" placeholder=" ">
			<label for="end" class="label">Скачивать до главы</label>
		</div>
		<p class="form-row-description"><em>Порядковый номер главы</em></p>
		<?php } ?>
		<?php if( isset( $payload['formats'] ) && $payload['formats'] ) { ?>
		<div class="form-row select">
			<select class="input" id="format" name="format">
				<?php foreach ($payload['formats'] as $key => $value) { ?>
				<option value="<?=$key?>"><?=$value?></option>
				<?php } ?>
			</select>
			<label for="format" class="label">Формат</label>
		</div>
		<?php } ?>
		<?php if( isset( $payload['use_auth'] ) && $payload['use_auth'] ) { ?>
		<div class="form-row select">
			<select class="input" id="auth" name="auth">
				<?php foreach ($payload['use_auth'] as $key => $value) { ?>
				<option value="<?=$key?>"><?=$value?></option>
				<?php } ?>
			</select>
			<label for="auth" class="label">Авторизация</label>
		</div>
		<?php } ?>
		<?php if( isset( $payload['use_images'] ) && $payload['use_images'] ) { ?>
		<div class="form-row checkbox">
			<label class="switch">
				<input class="input" type="checkbox" id="images" value="1" name="images" <?=($payload['images']?'checked':'')?> placeholder=" ">
				<div class="slider"></div>
			</label>
			<label for="images" class="label">Скачивать картинки</label>
		</div>
		<?php } ?>
		<?php if( isset( $payload['use_cover'] ) && $payload['use_cover'] ) { ?>
		<div class="form-row checkbox">
			<label class="switch">
				<input class="input" type="checkbox" id="cover" value="1" name="cover" <?=($payload['cover']?'checked':'')?> placeholder=" ">
				<div class="slider"></div>
			</label>
			<label for="images" class="label">Скачивать обложку</label>
		</div>
		<?php } ?>
		<?php /* if( isset( $payload['use_images'] ) ) { ?>
		<div class="form-row checkbox2">
			<label class="Checkbox">
				<input type="checkbox" id="images" name="images" <?=($payload['images']?'checked':'')?>>
				<div class="Checkbox-main">
					<span class="label" dir="auto">Скачивать картинки</span>
				</div>
			</label>
		</div>
		<?php } */ ?>
		<div class="settings-item-description">
			<hr>
			<h3>Маленький FAQ</h3>
			<details>
				<summary>Хочу скачать часть глав</summary>
				<h4><em>ПОСЛЕДНИЕ</em> N глав</h4>
				<p>Поле <code>Скачивать c главы</code> - введите значение <code>-N</code> (с "-" в начале)</p>
				<p>Поле <code>Скачивать до главы</code> - оставьте ПУСТЫМ</p>
				<small>Например, скачать последние 30 глав <code>Скачивать c главы = -30</code></small>
				<hr>
				<h4><em>ПЕРВЫЕ</em> N глав</h4>
				<p>Поле <code>Скачивать с главы</code> - оставьте ПУСТЫМ</p>
				<p>Поле <code>Скачивать до главы</code> - введите значение <code>N</code></p>
				<small>Например, скачать первые 30 глав <code>Скачивать до главы = 30</code></small>
				<hr>
				<h4>Главы начиная с N</h4>
				<p>Поле <code>Скачивать с главы</code> - введите значение <code>N</code></p>
				<small>Например, скачать начиная с 30 главы <code>Скачивать с главы = 30</code></small>
				<hr>
				<h4>Главы заканчивая N</h4>
				<p>Поле <code>Скачивать до главы</code> - введите значение <code>N</code></p>
				<small>Например, скачать до 30 главы <code>Скачивать до главы = 30</code></small>
				<hr>
				<h4>Главы заканчивая N с конца</h4>
				<p>Поле <code>Скачивать до главы</code> - введите значение <code>-N</code> (с "-" в начале)</p>
				<small>Например, скачать до 30 главы с конца <code>Скачивать до главы = -30</code></small>
				<hr>
				<h4>Главы с N до Y</h4>
				<p>Поле <code>Скачивать с главы</code> - введите значение <code>N</code></p>
				<p>Поле <code>Скачивать до главы</code> - введите значение <code>Y</code></p>
				<small>Например, скачать до с 5 по 30 главы <code>Скачивать с главы = 5</code> и <code>Скачивать до главы = 30</code></small>
			</details>
			<br>
			<details>
				<summary>Что такое ПОРЯДКОВЫЙ номер</summary>
				<table>
					<thead>
						<tr>
							<th><em>Порядковый номер</em></th>
							<th><em>Текст</em></th>
						</tr>
					</thead>
					<tbody>
						<tr>
							<td>1</td>
							<td>Пролог</td>
						</tr>
						<tr>
							<td>2</td>
							<td>Глава 1</td>
						</tr>
						<tr>
							<td>3</td>
							<td>Глава 1.1</td>
						</tr>
						<tr>
							<td>4</td>
							<td>Глава 2</td>
						</tr>
						<tr>
							<td>5</td>
							<td>Глава 2.1</td>
						</tr>
						<tr>
							<td>6</td>
							<td>Глава 2.2</td>
						</tr>
						<tr>
							<td>7</td>
							<td>Глава 3</td>
						</tr>
						<tr>
							<td>8</td>
							<td>3.1</td>
						</tr>
						<tr>
							<td>9</td>
							<td>Бонусная глава</td>
						</tr>
						<tr>
							<td>10</td>
							<td>Эпилог</td>
						</tr>
					</tbody>
				</table>
			</details>
		</div>
	</form>
</body>
</html>