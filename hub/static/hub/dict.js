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
        richEditors.forEach(hydrateEditor);
    }

    function copyNames(e) {
        const names = [
            document.forms.main.nameFR.value,
            document.forms.main.nameEN.value,
            document.forms.main.nameCN.value,
        ];
        navigator.clipboard.writeText(names.join("\t"))
    }

    window.addEventListener("load", function(e) {
        hydrateRichEditors(document);
    });

    window.dict = {
        hydrateRichEditors,
        copyNames,
    };
}());