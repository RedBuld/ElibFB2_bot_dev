var tg = window.Telegram.WebApp;

tg.MainButton.setText("Авторизоваться");
tg.MainButton.disable();
tg.MainButton.hide();

var login = false;
var password = false;

var html_form = document.getElementById("auth");
var login_input = document.getElementById("login");
var password_input = document.getElementById("password");

login_input.addEventListener('change',function()
{
   login = login_input.value != '';
   maybe_allow_send();
})
password_input.addEventListener('change',function()
{
   password = password_input.value != '';
   maybe_allow_send();
})

function maybe_allow_send()
{
   if(login && password)
   {
      tg.MainButton.enable();
      tg.MainButton.show();
   }
   else
   {
      tg.MainButton.disable();
      tg.MainButton.hide();
   }
}

Telegram.WebApp.onEvent('mainButtonClicked', function(){
   var formData = new FormData(html_form);
   var form = {};
   for(var pair of formData.entries()) {
      form[ pair[0] ] = pair[1];
   }
   var str = JSON.stringify(form);
   Telegram.WebApp.sendData(str); 
});