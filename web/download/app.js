var tg = window.Telegram.WebApp;

tg.MainButton.setText("Скачать");
tg.MainButton.enable();
tg.MainButton.show();

var html_form = document.getElementById("download_config");

Telegram.WebApp.onEvent('mainButtonClicked', function(){
   var formData = new FormData(html_form);
   var form = {};
   for(var pair of formData.entries()) {
      form[ pair[0] ] = pair[1];
   }
   var str = JSON.stringify(form);
   console.log(str);
   Telegram.WebApp.sendData(str); 
});