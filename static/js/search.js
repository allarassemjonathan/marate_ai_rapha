document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('addForm');
  const resultsTable = document.getElementById('resultsTable');
  const searchBox = document.getElementById('searchBox');
  const editModalOverlay = document.getElementById('editModalOverlay');
  const editForm = document.getElementById('editForm');
  
  let currentPatientId = null;
  let visibleColumns = []; // Will be loaded dynamically
  let columnHeaders = {}; // Will be loaded dynamically

  const userType = window.USER_TYPE;
  console.log(userType);
  console.log("userType");

  // Load dynamic column configuration
  async function loadColumnConfiguration() {
    try {
      const response = await fetch('/api/columns');
      const data = await response.json();
      
      visibleColumns = data.visible_columns.map(col => col.column_name); // column names
      columnHeaders = {};
      
      data.visible_columns.forEach(col => {
        columnHeaders[col.column_name] = col.display_name; // column_name -> display_name
      });
      
      console.log('Loaded visible columns:', visibleColumns);
      console.log('Loaded column headers:', columnHeaders);
      
      return true;
    } catch (error) {
      console.error('Error loading column configuration:', error);
      // Fallback to default configuration
      const columnVisibility = {
        'medecins': ['created_at', 'name','adresse','phone_number', 'meeting', 'new_cases', 'age','poids','taille','tension_arterielle','temperature','hypothese_de_diagnostique', 'renseignements_clinique', 'bilan','resultat_bilan', 'ordonnance', 'signature'],
        'infirmiers': ['created_at', 'name','adresse','phone_number', 'meeting', 'new_cases','age','poids','taille','tension_arterielle','temperature'],
        'receptionistes': ['created_at', 'name','adresse','phone_number','meeting', 'new_cases','age', 'meeting', 'new_cases', 'phone_number']
      };

      const defaultColumnHeaders = {
        'created_at': 'Date de création',
        'name': 'Nom',
        'adresse': 'Adresse',
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
      
      visibleColumns = columnVisibility[userType] || [];
      columnHeaders = defaultColumnHeaders;
      return false;
    }
  }

  function createTableHeaders(){
    const tableHeader = document.getElementById('tableHeader');
    tableHeader.innerHTML = '';

    visibleColumns.forEach(columnKey => {
      const th = document.createElement('th');
      th.className = "p-4 text-left text-cyan-400 font-semibold uppercase text-xs tracking-wider";
      th.textContent = columnHeaders[columnKey] || columnKey;
      tableHeader.appendChild(th);
    });
  }

  // Function to create dynamic form fields for adding patients
  function createDynamicFormFields() {
    const form = document.getElementById('addForm');
    const submitButton = form.querySelector('button[type="submit"]').parentElement;
    
    // Remove existing dynamic fields but keep submit button
    const existingFields = form.querySelectorAll('.dynamic-field');
    existingFields.forEach(field => field.remove());
    
    visibleColumns.forEach(columnKey => {
      // Skip system fields that shouldn't be in the add form
      if (columnKey === 'id' || columnKey === 'created_at') return;
      
      const fieldContainer = document.createElement('div');
      fieldContainer.className = 'relative dynamic-field';
      
      const displayName = columnHeaders[columnKey] || columnKey;
      let inputElement;
      
      // Create appropriate input type based on column name and type
      if (columnKey === 'date_of_birth') {
        inputElement = document.createElement('input');
        inputElement.type = 'date';
      } else if (columnKey.includes('age') || columnKey.includes('poids') || columnKey.includes('taille') || columnKey.includes('temperature')) {
        inputElement = document.createElement('input');
        inputElement.type = 'number';
        if (columnKey.includes('poids') || columnKey.includes('taille') || columnKey.includes('temperature')) {
          inputElement.step = '0.1';
        }
      } else if (columnKey.includes('tension_arterielle')) {
        inputElement = document.createElement('input');
        inputElement.type = 'text';
      } else if (columnKey.includes('diagnostique') || columnKey.includes('ordonnance') || columnKey.includes('bilan') || columnKey.includes('signature') || columnKey.includes('renseignements')) {
        inputElement = document.createElement('textarea');
        inputElement.className = 'input-field w-full p-4 rounded-xl h-20';
      } else {
        inputElement = document.createElement('input');
        inputElement.type = 'text';
      }
      
      if (inputElement.tagName !== 'TEXTAREA') {
        inputElement.className = 'input-field w-full p-4 rounded-xl';
      }
      
      inputElement.name = columnKey;
      inputElement.placeholder = displayName;
      
      // Make name field required
      if (columnKey === 'name') {
        inputElement.required = true;
      }
      
      fieldContainer.appendChild(inputElement);
      
      // Add the underline animation
      const underline = document.createElement('div');
      underline.className = 'absolute left-0 bottom-0 h-0.5 w-0 bg-gradient-to-r from-cyan-400 to-purple-500 transition-all duration-300 input-underline';
      fieldContainer.appendChild(underline);
      
      // Insert before submit button
      form.insertBefore(fieldContainer, submitButton);
      
      // Add focus/blur event listeners for underline animation
      inputElement.addEventListener('focus', function() {
        underline.style.width = '100%';
      });
      
      inputElement.addEventListener('blur', function() {
        underline.style.width = '0';
      });
    });
  }

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

function loadPatients(q = '') {
  fetch(`/search?q=${encodeURIComponent(q)}`)
    .then(res => res.json())
    .then(data => {
      resultsTable.innerHTML = '';
      data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      data = data.slice(0, 20);

      let currentActionRow = null;
      let currentHighlightedRow = null;

      data.forEach(p => {
        const tr = document.createElement('tr');
        tr.className = "cursor-pointer hover:bg-blue-50 transition-colors duration-200";

        visibleColumns.forEach(k => {
          const td = document.createElement('td');
          td.className = "p-2 border text-black";

          if (k == 'age' && p[k]) p[k] += ' ans';
          if (k == 'poids' && p[k]) p[k] += ' kg';
          if (k == 'taille' && p[k]) p[k] += ' cm';
          if (k == 'tension_arterielle' && p[k]) p[k] += ' mmHg';
          if (k == 'temperature' && p[k]) p[k] += ' °C';
          if (k == 'date_of_birth' && typeof p[k] === 'string') {
            p[k] = new Date(p[k]).toISOString().split('T')[0];
          }
          if (k === 'created_at' && typeof p[k] === 'string') {
            const date = new Date(p[k]);
            p[k] = date.toISOString().replace('T', ' ').split('.')[0];
          }

          let content = p[k] || '';
          if (content.length > 30) content = content.substring(0, 30) + '...';

          td.textContent = content;
          td.title = p[k] || '';
          tr.appendChild(td);
        });

        // Action row (initially hidden)
        const actionRow = document.createElement('tr');
        actionRow.className = "hidden bg-gray-50";
        const actionCell = document.createElement('td');
        actionCell.colSpan = visibleColumns.length + 1;
        let safeJson;
        try {
          safeJson = btoa(unescape(encodeURIComponent(JSON.stringify(p))));
        } catch (err) {
           console.error("❌ Encoding error for patient:", p.id);
          console.error("Problematic patient data:", p);
          console.error("First few fields:", {
            name: p.name,
            adresse: p.adresse,
            telephone: p.telephone
          });
          safeJson = ""; // or handle differently
        }
        actionCell.innerHTML = `
          <div class="flex space-x-4 items-center justify-center p-2 text-sm">
            <button class="text-blue-500 hover:text-blue-700" onclick="editPatient(${p.id})">Modifier</button>
            <button class="text-red-500 hover:text-red-700" onclick="deletePatient(${p.id})">Supprimer</button>
            <button class="text-green-500 hover:text-green-700" onclick="window.location.href='/patient/${p.id}'">Détails</button>
            <button
              class="text-yellow-500 hover:text-yellow-600"
              data-patient='${safeJson}'
              onclick="openInvoiceFromButton(this)"
            >Facture</button>
          </div>
        `;

        actionRow.appendChild(actionCell);

        // Toggle behavior
        tr.onclick = () => {
          const isSameRow = currentActionRow === actionRow;

          // If same row clicked again → hide it
          if (isSameRow) {
            actionRow.classList.add('hidden');
            tr.classList.remove('bg-blue-100');
            currentActionRow = null;
            currentHighlightedRow = null;
          } else {
            // Hide previous, show current
            if (currentActionRow) currentActionRow.classList.add('hidden');
            if (currentHighlightedRow) currentHighlightedRow.classList.remove('bg-blue-100');

            actionRow.classList.remove('hidden');
            tr.classList.add('bg-blue-100');

            currentActionRow = actionRow;
            currentHighlightedRow = tr;
          }
        };

        resultsTable.appendChild(tr);
        resultsTable.appendChild(actionRow);
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
      console.log(data.date_of_birth);
      // Populate all fields based on visible columns
      visibleColumns.forEach(field => {
        const input = document.getElementById(`edit_${field}`);
        if (input) {
          console.log(input);
          input.value = data[field] || '';
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
  editForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const patientId = document.getElementById('editId').value;
    const formData = new FormData(editForm);
    const data = Object.fromEntries(formData.entries());
    
    // Remove the ID field from the data to be sent
    delete data.id;
    
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
    createTableHeaders();
    createDynamicFormFields();
    loadPatients();
  });
});