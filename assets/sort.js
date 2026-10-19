/* 表の見出しを押すと並べ替える（table.sortable）。数字は「1,234」「12.3%」も数として比べる。 */
(function () {
  [].forEach.call(document.querySelectorAll("table.sortable"), function (t) {
    var ths = t.tHead.rows[0].cells;
    [].forEach.call(ths, function (th, i) {
      th.style.cursor = "pointer";
      th.setAttribute("role", "button");
      th.title = "押すと並べ替え";
      th.addEventListener("click", function () {
        var desc = th.getAttribute("aria-sort") !== "descending";
        [].forEach.call(ths, function (x) { x.removeAttribute("aria-sort"); });
        th.setAttribute("aria-sort", desc ? "descending" : "ascending");
        var body = t.tBodies[0], rows = [].slice.call(body.rows);
        function v(r) {
          var s = r.cells[i].textContent.replace(/[,%件人]/g, "").trim();
          var n = parseFloat(s);
          return isNaN(n) ? (i === 0 ? null : -1) : n;
        }
        rows.sort(function (a, b) {
          var x = v(a), y = v(b);
          if (x === null) return 0; // 区名の列は元の順（区コード順）に戻す
          return desc ? y - x : x - y;
        });
        if (i === 0) rows.sort(function (a, b) { return a._o - b._o; });
        rows.forEach(function (r) { body.appendChild(r); });
        if (typeof gtag === "function") gtag("event", "table_sort", { col: th.textContent });
      });
    });
    [].forEach.call(t.tBodies[0].rows, function (r, k) { r._o = k; });
  });
})();
