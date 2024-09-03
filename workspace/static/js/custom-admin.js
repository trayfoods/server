window.addEventListener("load", function () {
  (function ($) {
    $(document).ready(function () {
      // Change the campus field to a select field
      var campusField = $("#id_campus");
      const currentValue = campusField.val();
      campusField.replaceWith('<select id="id_campus" name="campus"></select>');
      campusField = $("#id_campus");
      // get current value
      function filterCampus() {
        var url =
          "/users/get-filtered-campus/?selected_school=" +
          $("#id_school option:selected").val();
        // Create loader element
        var loader = document.createElement("div");
        loader.id = "loader";
        loader.style.display = "none";
        loader.style.position = "fixed";
        loader.style.zIndex = "9999";
        loader.style.left = "0";
        loader.style.top = "0";
        loader.style.width = "100%";
        loader.style.height = "100%";
        loader.style.overflow = "visible";
        loader.style.backgroundColor = "rgba(0,0,0,0.5)";

        // Create spinner element
        var spinner = document.createElement("div");
        spinner.style.position = "absolute";
        spinner.style.top = "50%";
        spinner.style.left = "50%";
        spinner.style.width = "50px";
        spinner.style.height = "50px";
        spinner.style.backgroundColor = "#333";
        spinner.style.borderRadius = "50%";
        spinner.style.border = "3px solid #fff";
        spinner.style.borderTop = "3px solid transparent";
        spinner.style.animation = "spin 1s infinite linear";
        spinner.style.transform = "translate(-50%, -50%)";

        // Add spinner to loader
        loader.appendChild(spinner);

        // Add loader to body
        document.body.appendChild(loader);

        // Add spin animation to stylesheet
        var style = document.createElement("style");
        style.type = "text/css";
        style.innerHTML =
          "@keyframes spin { 0% { transform: translate(-50%, -50%) rotate(0deg); } 100% { transform: translate(-50%, -50%) rotate(360deg); } }";
        document.getElementsByTagName("head")[0].appendChild(style);

        // Show loader
        loader.style.display = "block";

        $.ajax({
          url: url,
          success: function (data) {
            var dropdown = $("#id_campus");
            // add the empty option
            dropdown.empty();
            dropdown.append(
              $("<option></option>").attr("value", "").text("---------")
            );
            $.each(data, function (index, item) {
              if (item === currentValue) {
                dropdown.append(
                  $('<option selected="true"></option>')
                    .attr("value", item)
                    .text(item)
                );
              } else {
                dropdown.append(
                  $("<option></option>").attr("value", item).text(item)
                );
              }
            });
          },
          complete: function () {
            loader.style.display = "none"; // Hide the loader
            document.body.removeChild(loader); // Remove the loader element
          },
        });
      }
      $(".school-field").change(filterCampus);
      if ($("#id_school option:selected").val()) {
        filterCampus();
      }
    });
  })(django.jQuery);
});
