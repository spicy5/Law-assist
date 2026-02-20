function openModal(card) {
  const name = card.dataset.name;
  const bar = card.dataset.bar;
  const lic = card.dataset.lic;
  const year = card.dataset.year;
  const phone = card.dataset.phone;
  const email = card.dataset.email;
  const address = card.dataset.address;
  const expert = card.dataset.areaexpert;

  document.getElementById("m-name").textContent = name;
  document.getElementById("m-bar").textContent = "Bar ID: " + bar;
  document.getElementById("m-lic").textContent = "License: " + lic;
  document.getElementById("m-year").textContent = "Year: " + year;
  document.getElementById("m-phone").textContent = "Phone: " + phone;
  document.getElementById("m-email").textContent = "Email: " + email;
  document.getElementById("m-address").textContent = "Court Address: " + address;
  document.getElementById("m-areaexpert").textContent = "Expertise: " + expert;

  document.getElementById("advocateModal").style.display = "block";
}

// ✅ Move this OUTSIDE of openModal()
function uploadCase() {
  const name = document.getElementById("m-name").textContent;
  const bar = document.getElementById("m-bar").textContent.replace("Bar ID: ", "");
  const url = `/client_caseup?adv_name=${encodeURIComponent(name)}&bar_id=${encodeURIComponent(bar)}`;
  window.location.href = url;
}

function closeModal() {
  document.getElementById("advocateModal").style.display = "none";
}
