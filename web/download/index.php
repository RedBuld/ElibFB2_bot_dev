<?php $payload = json_decode($_GET['payload'],true); ?>
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
		<?php } ?>
		<?php if( isset( $payload['use_end'] ) && $payload['use_end'] ) { ?>
		<div class="form-row">
			<input class="input" type="number" id="end" name="end" inputmode="numeric" placeholder=" ">
			<label for="end" class="label">Скачивать до главы</label>
		</div>
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
		<p class="settings-item-description">Если вы хотите скачать последние N глав, просто введите в поле <code>Скачивать c главы</code> значение с "-" в начале, например: Последние 30 глав = <code>-30</code>и оставьте поле <code>Скачивать до главы</code> ПУСТЫМ</p>
	</form>
</body>
</html>