document.addEventListener('DOMContentLoaded', function() {
    // Handle candidate button clicks
    document.querySelectorAll('.candidate-button').forEach(function(button) {
        button.addEventListener('click', function() {
            var candidate = this.value;
            document.getElementById(candidate).value = 'yes';
        });
    });
});
document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("biden-btn").addEventListener("click", function() {
        document.getElementById("biden").value = "1";
        document.getElementById("trump").value = "0";
        document.getElementById("voting-form").submit();
    });


    document.getElementById("trump-btn").addEventListener("click", function() {
        document.getElementById("biden").value = "0";
        document.getElementById("trump").value = "1";
        document.getElementById("voting-form").submit();
    });
});
