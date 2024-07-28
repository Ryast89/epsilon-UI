function toggle() {
  console.log("function triggered")
  var text = document.getElementsByClassName('content-rendered');
  var bbcode = document.getElementsByClassName('content-bbcode');

  var checkbox = document.getElementById("toggle");
  var setting = checkbox.checked;
  console.log(setting);
  if(setting == true) {
    console.log(setting);
    for(var i = 0; i < text.length;i++) {
      text[i].style.display = "none";
      bbcode[i].style.display = "block";
    }
  }

  else {
    console.log(setting);
    for(var i = 0; i < text.length;i++) {
      text[i].style.display = "block";
      bbcode[i].style.display = "none";
    }

}
}
function openNav() {
  document.getElementById("menu").style.transform = "translateX(0)";
}

function closeNav() {
  document.getElementById("menu").style.transform = "translateX(100%)";
}

function copy(element) {

  element.style.color = "green";

  console.log("Copy..\n....");
  var text = element.parentElement.previousElementSibling.children[3].innerHTML.replaceAll("<br>","\n");
  console.log("Text:");
  console.log(text);
  navigator.clipboard.writeText(text);
}