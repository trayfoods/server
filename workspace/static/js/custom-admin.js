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
        });
      }
      $(".school-field").change(filterCampus);
      filterCampus();
    });
  })(django.jQuery);
});
