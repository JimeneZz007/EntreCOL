

document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('filter-form');
    
    function setupFilterForm() {
        if (!filterForm) return;
        
        const formControls = filterForm.querySelectorAll('select, input[type="text"]');
        

        formControls.forEach(control => {
            control.addEventListener('change', function() {
               
                // filterForm.submit(); autoaplical filttro
            });
        });
        

        const btnLimpiar = document.getElementById('btn-limpiar');
        if (btnLimpiar) {
            btnLimpiar.addEventListener('click', function(e) {
                e.preventDefault();
                
              
                formControls.forEach(control => {
                    if (control.tagName === 'SELECT') {
                        control.selectedIndex = 0;
                    } else {
                        control.value = '';
                    }
                });
                
          
                filterForm.submit();
            });
        }
    }
    
    setupFilterForm();
    
    window.addEventListener('scroll', function() {
        const btnTop = document.getElementById('btn-top');
        if (!btnTop) return;
        
        if (window.scrollY > 300) {
            btnTop.classList.add('show');
        } else {
            btnTop.classList.remove('show');
        }
    });
    
    const btnTop = document.getElementById('btn-top');
    if (btnTop) {
        btnTop.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
});