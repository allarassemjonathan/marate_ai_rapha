document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('addForm');
  const resultsTable = document.getElementById('resultsTable');
  const searchBox = document.getElementById('searchBox');
  const editModalOverlay = document.getElementById('editModalOverlay');
  const editForm = document.getElementById('editForm');
  
  let currentPatientId = null;
// class="p-4 text-left text-cyan-400 font-semibold uppercase text-xs tracking-wider"
  const userType = window.USER_TYPE;
  console.log(userType);
  console.log("userType");
  // Define which columns each user type can see
  const columnVisibility = {
    'medecins': ['created_at', 'name','date_of_birth','adresse','age','poids','taille','tension_arterielle','temperature','hypothese_de_diagnostique', 'renseignements_clinique', 'bilan','resultat_bilan', 'ordonnance', 'signature'], // Columns 1-3
    'infirmiers': ['created_at', 'name','date_of_birth','adresse','age','poids','taille','tension_arterielle','temperature'], // Columns 4-7  
    'receptionistes': ['created_at', 'name','date_of_birth','adresse','age','poids','taille','tension_arterielle','temperature','hypothese_de_diagnostique', 'renseignements_clinique', 'bilan','resultat_bilan', 'ordonnance', 'signature'] // Column 8
  };

    const columnHeaders = {
    'created_at': 'Date de création',
    'name': 'Nom',
    'date_de_naissance': 'Date de naissance',
    'date_of_birth':'Date de naissance',
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
    'signature':'Signature'
  };

  function createTableHeaders(){
    const visibleColumns = columnVisibility[userType] || [];
    tableHeader.innerHTML = '';

    visibleColumns.forEach(columnKey => {
      const th = document.createElement('th');
      th.className = "p-4 text-left text-cyan-400 font-semibold uppercase text-xs tracking-wider";
      th.textContent = columnHeaders[columnKey] || columnKey;
      tableHeader.appendChild(th);
  });}

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

  function loadPatients(q = '') {
    fetch(`/search?q=${encodeURIComponent(q)}`)
      .then(res => res.json())
      .then(data => {
        resultsTable.innerHTML = '';
        data.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        data =data.slice(-20);
        data.forEach(p => {
          const tr = document.createElement('tr');
          tr.className = "cursor-pointer";

          // Open invoice modal when clicking the row
          tr.onclick = () => openInvoiceModal(p);
          
          // Get the visibility columns for current user type
          const visibleColumns = columnVisibility[userType] || [];

          // The rest of the fields
          visibleColumns.forEach(k => {
          const td = document.createElement('td');
          td.className = "p-2 border text-black";
          if (k == 'age' && p[k]!=null && p[k]!=''){
            p[k] = p[k] + ' ans'
          }
          else if (k == 'poids' && p[k]!=null && p[k]!=''){
            p[k] = p[k] + ' kg'
          }
          else if (k =='taille' && p[k]!=null && p[k]!=''){
            p[k] = p[k] + ' cm'
          }
          else if (k == 'tension_arterielle' && p[k]!=null && p[k]!='') {
            p[k] = p[k] + ' mmHg'
          }
          // else if (k == 'temperature' && p[k]!=null && p[k]!=''){
          //   p[k] = p[k] + ' °C'
          // }
          if (k == 'created_at' || k=='date_of_birth' && typeof p[k] == 'string' && p[k]!=''){
            p[k] = new Date(p[k]).toISOString().split('T')[0];
          }
          let content = p[k] || '';
          if (content.length > 30) {
            content = content.substring(0, 30) + '...';
          }
          td.textContent = content;
          td.title = p[k] || '';
          tr.appendChild(td);
        });
          
        // Action buttons
        const actionTd = document.createElement('td');
        actionTd.className = "p-2 border";
        actionTd.innerHTML = `
          <div class="flex space-x-2 justify-center">
            <button class="text-blue-500 hover:text-blue-700" onclick="event.stopPropagation(); editPatient(${p.id})">Modifier</button>
            <button class="text-red-500 hover:text-red-700" onclick="event.stopPropagation(); deletePatient(${p.id})">Supprimer</button>
          </div>
        `;
        tr.appendChild(actionTd);
        resultsTable.prepend(tr);
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
      .then(res => res.json())
      .then(patient => {
        // Populate the edit form
        document.getElementById('editId').value = patient.id;
        document.getElementById('edit_name').value  = patient.name;

        // Populate all fields
        const fields = columnVisibility[userType];
        fields.forEach(field => {
          const input = document.getElementById(`edit_${field}`);
          if (input) {
            input.value = patient[field] || '';
          }
          if (field=='created_at'){
            const createdDate = patient.created_at
            ? new Date(patient.created_at).toISOString().split('T')[0]
            : '';

            document.getElementById('edit_created_at').value = createdDate;
            console.log(patient);
          }
        });
        
        // Show the modal
        document.getElementById('editModalOverlay').classList.remove('hidden');
      });
  };

  window.closeEditModal = function() {
    document.getElementById('editModalOverlay').classList.add('hidden');
  };
  
  // Event delegation for clicks outside the modal content
  editModalOverlay.addEventListener('click', (e) => {
    if (e.target === editModalOverlay) {
      closeEditModal();
    }
  });

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


  // Initial load
  createTableHeaders();
  loadPatients();
});