function changeTable() {
  const table = document.querySelector('.alternative_table');

  const rows = document.querySelectorAll('tr');
  const rowsArray = Array.from(rows);
  const rowIndex = rowsArray.findIndex(row => row.contains(event.target));

  const columns = Array.from(rowsArray[rowIndex].querySelectorAll('td'));

  table.rows[rowIndex].cells[0].innerHTML = table.rows[rowIndex].cells[1].getElementsByTagName("select")[0].value;
}

document.addEventListener('DOMContentLoaded', function() {
  var elems = document.querySelectorAll('.tooltipped');
  var instances = M.Tooltip.init(elems, options);
});

function addI() {
  var ol = document.getElementById("dynamic-text");
  var option = document.getElementById("option");
  var li = document.createElement("li");
  li.setAttribute('id', option.value);
  li.appendChild(document.createTextNode(option.value));
  ol.appendChild(li);
}

function removeI() {
  var ol = document.getElementById("dynamic-text");
  var option = document.getElementById("option");
  var item = document.getElementById(option.value);
  ol.removeChild(item);
}

function addItem() {
  var ul = document.getElementById("dynamic-list");
  var candidate = document.getElementById("candidate");
  var li = document.createElement("li");
  li.setAttribute('id', candidate.value);
  li.appendChild(document.createTextNode(candidate.value));
  ul.appendChild(li);
}

function removeItem() {
  var ul = document.getElementById("dynamic-list");
  var candidate = document.getElementById("candidate");
  var item = document.getElementById(candidate.value);
  ul.removeChild(item);
}

function submit()
{
  alert("Your recipe was submitted successfully!");
}