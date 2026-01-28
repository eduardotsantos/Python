// Gestão P&D - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirm delete dialogs
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Tem certeza que deseja excluir?')) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Currency formatting for input fields
    document.querySelectorAll('input[data-currency]').forEach(function(input) {
        input.addEventListener('blur', function() {
            const val = parseFloat(this.value);
            if (!isNaN(val)) {
                this.value = val.toFixed(2);
            }
        });
    });

    // Progress slider for milestones
    document.querySelectorAll('.progress-slider').forEach(function(slider) {
        slider.addEventListener('input', function() {
            const label = document.getElementById('progress-label-' + this.dataset.milestoneId);
            if (label) {
                label.textContent = this.value + '%';
            }
        });

        slider.addEventListener('change', function() {
            const milestoneId = this.dataset.milestoneId;
            const projectId = this.dataset.projectId;
            const progress = this.value;

            fetch(`/projects/${projectId}/schedule/${milestoneId}/progress`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ progress: progress })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const statusEl = document.getElementById('status-' + milestoneId);
                    if (statusEl) {
                        statusEl.textContent = data.status;
                    }
                }
            })
            .catch(err => console.error('Error updating progress:', err));
        });
    });
});

// Refresh public calls with loading state
function refreshPublicCalls(button) {
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Atualizando...';

    fetch('/public-calls/refresh-ajax', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        let msg = `Atualizado! FINEP: ${data.finep} chamadas. BNDES: ${data.bndes} chamadas.`;
        if (data.errors && data.errors.length > 0) {
            msg += ' Erros: ' + data.errors.join('; ');
        }
        showToast(msg, data.errors && data.errors.length > 0 ? 'warning' : 'success');
        setTimeout(() => location.reload(), 1500);
    })
    .catch(err => {
        showToast('Erro ao atualizar chamadas: ' + err, 'danger');
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

function showToast(message, type) {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;top:70px;right:20px;z-index:9999;max-width:400px;';
    document.body.appendChild(container);
    return container;
}

// Format currency for display
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}
