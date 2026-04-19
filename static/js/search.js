window.populateDropdown = function(dropdownList) {
    dropdownList.innerHTML = '';
    
    // Group items by category
    const categories = {};
    Object.entries(serviceItems).forEach(([key, item]) => {
        if (!categories[item.category]) {
            categories[item.category] = [];
        }
        categories[item.category].push({key, ...item});
    });
    
    // Create dropdown items grouped by category
    Object.entries(categories).forEach(([category, items]) => {
        // Category header
        const categoryHeader = document.createElement('div');
        categoryHeader.className = 'px-3 py-2 bg-gray-100 text-gray-600 text-xs font-semibold uppercase tracking-wide';
        categoryHeader.textContent = category;
        dropdownList.appendChild(categoryHeader);
        
        // Category items
        items.forEach(item => {
            const dropdownItem = document.createElement('div');
            dropdownItem.className = 'dropdown-item flex justify-between items-center px-3 py-2 cursor-pointer hover:bg-gray-50 border-b border-gray-100';
            dropdownItem.innerHTML = `
                <span>${item.label}</span>
                <span class="text-gray-500 text-sm">${item.unitPrice.toLocaleString()} Fcfa</span>
            `;
            dropdownItem.onclick = () => window.selectService(dropdownItem, item);
            dropdownList.appendChild(dropdownItem);
        });
    });
};

window.toggleDropdown = function(input) {
    const container = input.closest('.dropdown-container');
    const dropdown = container.querySelector('.dropdown-list');
    
    // Close all other dropdowns
    document.querySelectorAll('.dropdown-container').forEach(otherContainer => {
        if (otherContainer !== container) {
            const otherDropdown = otherContainer.querySelector('.dropdown-list');
            otherDropdown.style.display = 'none';
            otherContainer.classList.remove('dropdown-open');
        }
    });
    
    // Toggle current dropdown
    const isVisible = dropdown.style.display === 'block';
    dropdown.style.display = isVisible ? 'none' : 'block';
    container.classList.toggle('dropdown-open', !isVisible);
    
    if (!isVisible) {
        window.populateDropdown(dropdown);
    }
};

window.filterDropdown = function(input) {
    const container = input.closest('.dropdown-container');
    const dropdown = container.querySelector('.dropdown-list');
    const searchTerm = input.value.toLowerCase();
    
    if (searchTerm.length === 0) {
        window.populateDropdown(dropdown);
        return;
    }
    
    dropdown.innerHTML = '';
    
    // Filter and display matching items
    Object.entries(serviceItems).forEach(([key, item]) => {
        if (item.label.toLowerCase().includes(searchTerm) || 
            item.category.toLowerCase().includes(searchTerm)) {
            
            const dropdownItem = document.createElement('div');
            dropdownItem.className = 'dropdown-item flex justify-between items-center px-3 py-2 cursor-pointer hover:bg-gray-50 border-b border-gray-100';
            dropdownItem.innerHTML = `
                <span>${item.label}</span>
                <span class="text-gray-500 text-sm">${item.unitPrice.toLocaleString()} Fcfa</span>
            `;
            dropdownItem.onclick = () => window.selectService(dropdownItem, item);
            dropdown.appendChild(dropdownItem);
        }
    });
    
    dropdown.style.display = 'block';
    container.classList.add('dropdown-open');
};

window.selectService = function(dropdownItem, serviceItem) {
    const container = dropdownItem.closest('.dropdown-container');
    const input = container.querySelector('.item-libelle');
    const articleRow = container.closest('.article-row');
    const quantiteInput = articleRow.querySelector('.item-quantite');
    const montantInput = articleRow.querySelector('.item-montant');
    
    // Set the service name and price
    input.value = serviceItem.label;
    montantInput.value = serviceItem.unitPrice;
    
    // Store the unit price as data attribute for future calculations
    montantInput.setAttribute('data-unit-price', serviceItem.unitPrice);
    
    // Update section subtotal
    const sectionDiv = articleRow.closest('.section-container');
    window.updateSectionSubtotal(sectionDiv);
    
    // Close dropdown
    const dropdown = container.querySelector('.dropdown-list');
    dropdown.style.display = 'none';
    container.classList.remove('dropdown-open');
};

window.addArticle = function(button) {
    const sectionDiv = button.closest('.section-container');
    const articleList = sectionDiv.querySelector('.articles-list');

    const row = document.createElement('div');
    row.className = 'article-row grid grid-cols-1 md:grid-cols-3 gap-4 items-center';

    // MODIFIED: Added dropdown container to libelle input
    row.innerHTML = `
        <div class="dropdown-container relative">
            <div class="relative">
                <input type="text" 
                       class="item-libelle input-field w-full p-3 rounded-xl border border-gray-600 pr-10" 
                       placeholder="Libellé" 
                       onclick="toggleDropdown(this)" 
                       oninput="filterDropdown(this)"
                       autocomplete="off"
                       required>
                <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                    <svg class="dropdown-arrow w-4 h-4 text-gray-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                </div>
            </div>
            <div class="dropdown-list absolute top-full left-0 right-0 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto" style="display: none;"></div>
        </div>
        <input type="number" class="item-quantite input-field w-full p-3 rounded-xl border border-gray-600" placeholder="Quantité" min="1" step="1" value="1" required>
        <input type="number" class="item-montant input-field w-full p-3 rounded-xl border border-gray-600" placeholder="Montant (Fcfa)" min="0" step="1" value="0" required>
        <div class="col-span-1 md:col-span-3 text-right">
            <button type="button" onclick="removeArticle(this)" class="text-red-500 hover:text-red-500 text-sm">Supprimer l'article</button>
        </div>
    `;

    articleList.appendChild(row);

    // Add event listeners to update subtotal when quantity or price changes
    const qtyInput = row.querySelector('.item-quantite');
    const priceInput = row.querySelector('.item-montant');

    [qtyInput, priceInput].forEach(input => {
        input.addEventListener('input', () => updateSectionSubtotal(sectionDiv));
    });

    // NEW: Populate dropdown for the new article
    const dropdownList = row.querySelector('.dropdown-list');
    populateDropdown(dropdownList);

    updateSectionSubtotal(sectionDiv);
};

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('addForm');
  // const resultsTable = document.getElementById('resultsTable');
  const searchBox = document.getElementById('searchBox');
  const editModalOverlay = document.getElementById('editModalOverlay');
  const editForm = document.getElementById('editForm');
  
  let currentPatientId = null;
  let visibleColumns = []; // Will be loaded dynamically
  let columnHeaders = {}; // Will be loaded dynamically

  const columnVisibility = {
        'medecins': ['created_at', 'name','adresse','phone_number', 'meeting', 'new_cases', 'age','poids','taille','tension_arterielle','temperature','hypothese_de_diagnostique', 'renseignements_clinique', 'bilan','resultat_bilan', 'ordonnance', 'signature'],
        'infirmiers': ['created_at', 'name','adresse','phone_number', 'meeting', 'new_cases','age','poids','taille','tension_arterielle','temperature'],
        'receptionistes': ['created_at', 'name','adresse','phone_number','meeting', 'new_cases','age', 'meeting', 'new_cases', 'phone_number']
      };

   const defaultColumnHeaders = {
        'created_at': 'Date de création',
        'name': 'Nom',
        'adresse': 'Adresse',
        'date_of_birth':'date de naissance',
        'age': 'Age',
        'poids': 'Poids',
        'taille': 'Taille',
        'tension_arterielle': 'Tension',
        'temperature': 'Température',
        'hypothese_de_diagnostique': 'Hypothèse de diagnostique',
        'renseignements_clinique':'Renseignement clinique',
        'bilan': 'Bilan',
        'resultat_bilan': 'Conclusion du bilan',
        'ordonnance': 'Ordonnance',
        'signature':'Signature', 
        'meeting':'Rendez-vous',
        'new_cases':'Nouveaux cas',
        'phone_number':'Numero de telephone'
      };
    
  const userType = window.USER_TYPE;
  console.log(userType);
  console.log("userType");

  // Load dynamic column configuration
  async function loadColumnConfiguration() {
    try {
      
    const response = await fetch(`/get_visibility/${userType}`);
    const data = await response.json();   // ✅ wait for JSON here
    console.log("Full JSON response:", data);

    visibleColumns = columnVisibility[userType] = data;
    columnHeaders = {};

    for (let i = 0; i < data.length; i++){
      columnHeaders[data[i]] = defaultColumnHeaders[data[i]]; // column_name -> display_name
    }

    console.log("Loaded visible columns:", visibleColumns);
    console.log("Loaded column headers:", columnHeaders);
      
      return true;
    } catch (error) {
      console.error('Error loading column configuration:', error);
      // Fallback to default configuration
      
      visibleColumns = columnVisibility[userType] || [];
      columnHeaders = defaultColumnHeaders;
      return false;
    }
  }

  // async function fetchVisibility() {
  //   const res = await fetch(`/get_visibility/${userType}`);
  //   console.log("ici");
  //   columnVisibility[userType] = await res.json();
  //   createTableHeaders();
  //   loadPatients();
  // }

  // Initial load when user logs in
  // fetchVisibility();

  function createTableHeaders(){
    const tableHeader = document.getElementById('tableHeader');
    tableHeader.innerHTML = '';

    visibleColumns.forEach(columnKey => {
      const th = document.createElement('th');
      th.className = "p-4 text-left text-black-400 font-semibold uppercase text-xs tracking-wider";
      th.textContent = columnHeaders[columnKey] || columnKey;
      tableHeader.appendChild(th);
    });
  }

  // // Function to create dynamic form fields for adding patients
  // function createDynamicFormFields() {
  //   const form = document.getElementById('addForm');
  //   const submitButton = form.querySelector('button[type="submit"]').parentElement;
    
  //   // Remove existing dynamic fields but keep submit button
  //   const existingFields = form.querySelectorAll('.dynamic-field');
  //   existingFields.forEach(field => field.remove());
    
  //   visibleColumns.forEach(columnKey => {
  //     // Skip system fields that shouldn't be in the add form
  //     if (columnKey === 'id' || columnKey === 'created_at') return;
      
  //     const fieldContainer = document.createElement('div');
  //     fieldContainer.className = 'relative dynamic-field';
      
  //     const displayName = columnHeaders[columnKey] || columnKey;
  //     let inputElement;
      
  //     // Create appropriate input type based on column name and type
  //     if (columnKey === 'date_of_birth') {
  //       inputElement = document.createElement('input');
  //       inputElement.type = 'date';
  //     } else if (columnKey.includes('age') || columnKey.includes('poids') || columnKey.includes('taille') || columnKey.includes('temperature')) {
  //       inputElement = document.createElement('input');
  //       inputElement.type = 'number';
  //       if (columnKey.includes('poids') || columnKey.includes('taille') || columnKey.includes('temperature')) {
  //         inputElement.step = '0.1';
  //       }
  //     } else if (columnKey.includes('tension_arterielle')) {
  //       inputElement = document.createElement('input');
  //       inputElement.type = 'text';
  //     } else if (columnKey.includes('diagnostique') || columnKey.includes('ordonnance') || columnKey.includes('bilan') || columnKey.includes('signature') || columnKey.includes('renseignements')) {
  //       inputElement = document.createElement('textarea');
  //       inputElement.className = 'input-field w-full p-4 rounded-xl h-20';
  //     } else {
  //       inputElement = document.createElement('input');
  //       inputElement.type = 'text';
  //     }
      
  //     if (inputElement.tagName !== 'TEXTAREA') {
  //       inputElement.className = 'input-field w-full p-4 rounded-xl';
  //     }
      
  //     inputElement.name = columnKey;
  //     inputElement.placeholder = displayName;
      
  //     // Make name field required
  //     if (columnKey === 'name') {
  //       inputElement.required = true;
  //     }
      
  //     fieldContainer.appendChild(inputElement);
      
  //     // Add the underline animation
  //     const underline = document.createElement('div');
  //     underline.className = 'absolute left-0 bottom-0 h-0.5 w-0 bg-gradient-to-r from-cyan-400 to-purple-500 transition-all duration-300 input-underline';
  //     fieldContainer.appendChild(underline);
      
  //     // Insert before submit button
  //     form.insertBefore(fieldContainer, submitButton);
      
  //     // Add focus/blur event listeners for underline animation
  //     inputElement.addEventListener('focus', function() {
  //       underline.style.width = '100%';
  //     });
      
  //     inputElement.addEventListener('blur', function() {
  //       underline.style.width = '0';
  //     });
  //   });
  // }

  // Make these functions globally accessible
  window.openInvoiceModal = function(patient) {
    currentPatientId = patient.id;
    document.getElementById('invoiceModal').style.display = 'flex';

    // Split full name into prenom and nom
    const fullName = (patient.name || '').trim();
    const parts = fullName.split(' ');
    const nom = parts.pop(); // Last word
    const prenom = parts.join(' '); // Everything before

    // Fill the modal inputs
    document.getElementById('input_prenom').value = prenom;
    document.getElementById('input_nom').value = nom;

    // Clear invoice items and add one
    document.getElementById('invoice-items-container').innerHTML = '';
    addInvoiceSection();
  };

  window.closeInvoiceModal = function() {
    document.getElementById('invoiceModal').style.display = 'none';
    currentPatientId = null;
    document.getElementById('invoice-items-container').innerHTML = '';
  };

  window.addInvoiceItem = function() {
    const itemsContainer = document.getElementById('invoice-items-container');
    const itemDiv = document.createElement('div');
    itemDiv.className = 'grid grid-cols-1 md:grid-cols-4 gap-5 mb-6 p-6 border border-gray-700 rounded-xl';
    
    itemDiv.innerHTML = `
        <div class="relative md:col-span-2">
            <input type="text" placeholder="Nom de l'article" class="item-name input-field w-full p-4 rounded-xl" required>
            <div class="absolute left-0 bottom-0 h-0.5 w-0 bg-gradient-to-r from-cyan-400 to-cyan-400 transition-all duration-300 input-underline"></div>
        </div>
        
        <div class="relative">
            <input type="number" placeholder="Quantité" class="item-quantity input-field w-full p-4 rounded-xl" step="0.01" min="0" required>
            <div class="absolute left-0 bottom-0 h-0.5 w-0 bg-gradient-to-r from-cyan-400 to-cyan-400 transition-all duration-300 input-underline"></div>
        </div>
        
        <div class="relative">
            <input type="number" placeholder="Prix unitaire" class="item-price input-field w-full p-4 rounded-xl" step="0.01" min="0" required>
            <div class="absolute left-0 bottom-0 h-0.5 w-0 bg-gradient-to-r from-cyan-400 to-cyan-400 transition-all duration-300 input-underline"></div>
        </div>
        
        <div class="md:col-span-4 flex justify-end">
            <button type="button" onclick="removeInvoiceItem(this)" class="text-red-400 hover:text-red-300 transition-colors text-sm">
                Supprimer cet article
            </button>
        </div>
    `;
    
    itemsContainer.appendChild(itemDiv);
    
    // Add focus/blur effects to the new inputs
    const newInputs = itemDiv.querySelectorAll('.input-field');
    newInputs.forEach(input => {
        input.addEventListener('focus', function() {
            const underline = this.nextElementSibling;
            if (underline && underline.classList.contains('input-underline')) {
                underline.style.width = '100%';
            }
        });
        
        input.addEventListener('blur', function() {
            const underline = this.nextElementSibling;
            if (underline && underline.classList.contains('input-underline')) {
                underline.style.width = '0';
            }
        });
    });
  };

  window.removeInvoiceItem = function(button) {
    const itemsContainer = document.getElementById('invoice-items-container');
    if (itemsContainer.children.length > 1) {
        button.closest('.grid').remove();
    } else {
        alert('Au moins un article est requis');
    }
  };

  window.generateInvoice = function generateInvoice() {
  if (!currentPatientId) {
    alert('Erreur: Aucun patient sélectionné');
    return;
  }

  // Gather meta info from patient inputs
  const meta = {
    nom: document.getElementById('input_nom').value.trim(),
    prenom: document.getElementById('input_prenom').value.trim(),
    police: document.getElementById('input_police').value.trim(),
    assurance: document.getElementById('input_assurance').value.trim(),
    pourcentage: document.getElementById('input_pourcentage').value.trim(),
    envoye_a: document.getElementById('input_envoye_a').value.trim()
  };

  const sections = [];
  const sectionDivs = document.querySelectorAll('#invoice-items-container .section-container');

  sectionDivs.forEach(sectionDiv => {
    const titre = sectionDiv.querySelector('.section-title-input').value.trim();
    const articles = [];
    const articleRows = sectionDiv.querySelectorAll('.article-row');

    articleRows.forEach(row => {
      const libelle = row.querySelector('.item-libelle').value.trim();
      const quantite = parseFloat(row.querySelector('.item-quantite').value);
      const montant = parseFloat(row.querySelector('.item-montant').value);

      if (libelle && quantite > 0 && montant >= 0) {
        articles.push({ libelle, quantite, montant });
      }
    });

    if (titre && articles.length > 0) {
      sections.push({ titre, articles });
    }
  });

  if (sections.length === 0) {
    alert('Veuillez ajouter au moins une section avec des articles valides.');
    return;
  }

  // Send to backend with meta
  fetch(`/generate_invoice/${currentPatientId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ meta, sections })
  })
  .then(response => {
    if (response.ok) return response.blob();
    else throw new Error('Erreur lors de la génération du PDF');
  })
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `facture_${meta.nom}_${meta.prenom}_${new Date().toISOString().slice(0,10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    closeInvoiceModal();
  })
  .catch(error => {
    alert('Erreur: ' + error.message);
  });
}

window.openInvoiceFromButton = function(button) {
  const raw = button.getAttribute('data-patient');
  const patient = JSON.parse(atob(raw));
  openInvoiceModal(patient);
};

let pageSize = 20;

const pageSizeInput = document.getElementById("pageSizeInput");
if (pageSizeInput) {
  pageSizeInput.addEventListener("input", e => {
    let val = parseInt(e.target.value, 10);

    // sécurité : si l'utilisateur vide le champ ou met 0/valeur négative
    if (isNaN(val) || val <= 0) {
      pageSize = 20; 
    } else {
      pageSize = val;
    }

    loadPatients(searchBox.value); // recharge la liste
  });
}

function loadPatients(q = '') {
  console.log('ran this');
  fetch(`/search?q=${encodeURIComponent(q)}`)
    .then(res => res.json())
    .then(data => {
      console.log('what is this');
      console.log(data);
      data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      data = data.slice(0, pageSize);

      let currentActionRow = null;
      let currentHighlightedRow = null;

      const patientsList = document.getElementById('patientsList');
      patientsList.innerHTML = '';
      console.log('trying to load');
      data.forEach(p => {
        if (p.age) {
          let ageFloat = parseFloat(p.age);
          let years = Math.floor(ageFloat);
          let months = Math.floor((ageFloat - years) * 12);
          p.age = `${years ? years + ' ans ' : ''}${months ? months + ' mois' : ''}`;
        }
        if (p.poids) p.poids += ' kg';
        if (p.taille) p.taille += ' cm';
        if (p.temperature) p.temperature += ' °C';
        if (p.created_at) {
          const date = new Date(p.created_at);
          p.created_at = date.toISOString().replace('T', ' ').split('.')[0];
        }

        const card = document.createElement('div');
        card.className = "flex items-center justify-between bg-white rounded-2xl shadow-md px-5 py-4 hover:shadow-lg transition-shadow duration-200";

        const raw = p.created_at;
        const date = new Date(raw.replace(" ", "T"));
        const formatted = date.toLocaleString("fr-TD", {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
            hour12: false,  // Chad uses 24-hour time
        })

        card.innerHTML = `
          <div class="flex items-center gap-4">
            <!-- Profile Icon -->
            <div class="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-400">
              <i class="fa-solid fa-user text-xl"></i>
            </div>

            <!-- Patient Info -->
            <div>
              <h2 class="text-base font-semibold text-gray-800">${p.name || 'Sans nom'}</h2>
              <p class="text-sm text-gray-500">${formatted + '· '  || ''} ${p.age || ''} ${p.poids ? '· ' + p.poids : ''} ${p.temperature ? '· ' + p.temperature : ''}</p>
              <p class="text-xs text-gray-400 mt-0.5"> 🕿 ${p.phone_number || ''}</p>
            </div>
          </div>

          <!-- Action icons -->
          <div class="flex gap-4 text-gray-500">
            <button title="Modifier" onclick="editPatient(${p.id})"><i class="fa-solid fa-pen hover:text-blue-600"></i></button>
            <button title="Supprimer" onclick="deletePatient(${p.id})"><i class="fa-solid fa-trash hover:text-red-600"></i></button>
            <button title="Détails" onclick="window.location.href='/patient/${p.id}'"><i class="fa-solid fa-eye hover:text-green-600"></i></button>
            <button title="Facture" data-patient='${btoa(unescape(encodeURIComponent(JSON.stringify(p))))}' onclick="openInvoiceFromButton(this)"><i class="fa-solid fa-file-invoice hover:text-yellow-600"></i></button>
          </div>
        `;

        patientsList.appendChild(card);
      });


    });
}



  window.deletePatient = function (id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce patient?')) {
      fetch(`/delete/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(() => {
          loadPatients(searchBox.value);
          showToast('Patient supprimé avec succès', 2500)
        });
    }
  }

window.editPatient = function(id) {
  fetch(`/get_patient/${id}`)
    .then(async res => {
      const data = await res.json();
      if (!res.ok || data.status === 'error') {
        // Show error flash message
        showToast(data.message || 'Une erreur est survenue lors de la récupération du patient.');
        return;
      }
      // Populate the edit form
      document.getElementById('editId').value = data.id;
      document.getElementById('edit_name').value = data.name;
      document.getElementById('edit_date_of_birth').value = data.date_of_birth;
      console.log(data.age);
      // Convert age into years, months, days

      if (data.age != undefined && data.age != null){
         const ageFloat = parseFloat(data.age);

        // Extract years, months, days
        const years = Math.floor(ageFloat);
        const months = Math.floor((ageFloat - years) * 12);
        const days = Math.floor((((ageFloat - years) * 12) - months) * 30);

        console.log(`Age parsed → ${years} years, ${months} months, ${days} days`);

        // Fill inputs if they exist in your form
        const yearInput = document.getElementById("edit_age_years");
        const monthInput = document.getElementById("edit_age_months");
        const dayInput = document.getElementById("edit_age_days");

        if (yearInput) yearInput.value = data['age_years'];
        if (monthInput) monthInput.value = data['age_months'];
        if (dayInput) dayInput.value = data['age_days'];
      }

      // Populate all fields based on visible columns
      visibleColumns.forEach(field => {
        const input = document.getElementById(`edit_${field}`);
        if (input) {
          console.log(input);
          input.value = data[field] || '';
        }
        if (field=='created_at'){
            const createdDate = data.created_at
            ? new Date(data.created_at).toISOString().split('T')[0]
            : '';

            document.getElementById('edit_created_at').value = createdDate;
            console.log("hereeeeeeeee");
          }
        if (field == 'date_of_birth'){
          const birthdate = data.date_of_birth
            ? new Date(data.date_of_birth).toISOString().split('T')[0]
            : '';
            console.log("birthday .. ");
            console.log(birthdate);

            document.getElementById('edit_date_of_birth').value = birthdate;
            console.log("here");
            console.log(data.date_of_birth);
        }
      });

      // Show the modal
      document.getElementById('editModalOverlay').classList.remove('hidden');
    })
    .catch(err => {
      console.error(err);
      showToast(" Erreur reseau. Impossible de récupérer les données du patient.");
    });
};


// Example flash message display function
function showFlash(message) {
  const flash = document.createElement('div');
  flash.className = 'bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative m-2';
  flash.role = 'alert';
  flash.innerHTML = `
    <strong class="font-bold">Erreur: </strong>
    <span class="block sm:inline">${message}</span>
  `;

  const flashContainer = document.getElementById('flash-container') || document.body;
  flashContainer.appendChild(flash);

  setTimeout(() => flash.remove(), 5000); // Auto-remove after 5 seconds
}

// Submit event for the edit form
// Submit event for the edit form
editForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const patientId = document.getElementById('editId').value;
  const formData = new FormData(editForm);
  const data = Object.fromEntries(formData.entries());
  delete data.id;

  // Show loader
  

  fetch(`/update/${patientId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  .then(res => res.json())
  .then(result => {
    if (result.status === 'success') {
      closeEditModal();
      loadPatients(searchBox.value);
      showToast('Patient modifié avec succès', 2500);
    } else {
      alert(result.message || 'Error updating patient');
    }
  })
  .catch(err => {
    console.error('Erreur de mise à jour:', err);
    alert('Erreur de connexion au serveur');
  })
  .finally(() => {
    // Hide loader regardless of outcome
    
  });
});


  // Add new patient form submission
  form.addEventListener('submit', e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    fetch('/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(() => {
      form.reset();
      closeAddPatientModal();
      loadPatients(searchBox.value);
      showToast('Patient ajouté avec succès', 2500);
    });
  });

  // Search functionality
  searchBox.addEventListener('input', e => {
    clearTimeout(window.searchTimer);
    window.searchTimer = setTimeout(() => loadPatients(e.target.value), 300);
  });

  function showToast(message, duration = 3000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.textContent = message;

  container.appendChild(toast);

  // Trigger show animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // Auto-remove after duration
  setTimeout(() => {
    toast.classList.remove('show');
    toast.addEventListener('transitionend', () => toast.remove());
  }, duration);
};


  // Initial load - load columns first, then setup table and load patients
  loadColumnConfiguration().then(() => {
    // createTableHeaders();
    //createDynamicFormFields();
    loadPatients();
  });
});