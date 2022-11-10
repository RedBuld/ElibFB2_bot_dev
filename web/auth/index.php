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
	<form id="auth">
		<div class="form-row">
			<input class="input" type="text" id="login" name="login" placeholder=" ">
			<label for="login" class="label">Логин</label>
		</div>
		<div class="form-row">
			<input class="input" type="text" id="password" name="password" placeholder=" ">
			<label for="password" class="label">Пароль</label>
		</div>
		<p class="settings-item-description"><center>!!!ВХОД ЧЕРЕЗ СОЦ. СЕТИ НЕВОЗМОЖЕН!!!</center></p>
	</form>
</body>
</html>