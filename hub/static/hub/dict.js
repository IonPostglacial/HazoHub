(function() {
    function hydrateEditor(editor) {
        if (typeof ClassicEditor === "undefined") return;
        ClassicEditor
            .create(editor)
            .catch(error => {
                console.error( error );
            });
    }
    
    function hydrateRichEditors(elt) {
        const richEditors = Array.from(elt.querySelectorAll(".ckeditor"));
        console.log(richEditors);
        richEditors.forEach(hydrateEditor);
    }

    window.addEventListener("load", function(e) {
        hydrateRichEditors(document);
    });

    window.dict = {
        hydrateRichEditors
    };
}());