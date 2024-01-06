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
        loader.innerHTML =
          '<div class="spinner" style="position: absolute; top: 50%; left: 50%; width: 50px; height: 50px; background-color: #333; border-radius: 50%; animation: spin 1s infinite linear; transform: translate(-50%, -50%);"></div>';
        document.body.appendChild(loader);

        loader.style.display = "block"; // Show the loader
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
      filterCampus();
    });
  })(django.jQuery);
});
