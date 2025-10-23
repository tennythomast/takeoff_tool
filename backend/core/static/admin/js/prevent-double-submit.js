(function($) {
    $(document).ready(function() {
        // Target all forms in the admin
        $('form').submit(function() {
            // Check if this form has already been submitted
            if ($(this).data('submitted') === true) {
                // Prevent duplicate submission
                console.log('Preventing duplicate form submission');
                return false;
            }
            
            // Mark the form as submitted
            $(this).data('submitted', true);
            
            // Enable submit button after a delay to allow for form resubmission if needed
            var form = $(this);
            setTimeout(function() {
                form.data('submitted', false);
            }, 3000); // 3 seconds delay
            
            // Allow the form to be submitted
            return true;
        });
    });
})(django.jQuery);
