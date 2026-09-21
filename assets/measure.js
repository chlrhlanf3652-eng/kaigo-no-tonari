/* かいごのとなり — 収益判定のための計測
 *
 * 何が収益につながるかは「どのページが読まれたか」では分からない。
 * 判断に要るのは、利用者が実際に事業所へ連絡した回数である。
 * このサイトでの「連絡した」は、ほぼ次の2つに絞られる。
 *
 *   1. 電話番号をタップした  … tel_tap
 *   2. 外部サイトへ出ていった … outbound_click
 *
 * GA4 の拡張計測イベントは tel: リンクを拾わないので、1 は自前で送る必要がある。
 * どちらもページ側の文脈（カテゴリ・エリア・事業所名）を一緒に送り、
 * 「どの区のどのページが連絡を生んでいるか」を後から区別できるようにしている。
 *
 * ついでに FAQ の開閉も送る。どの疑問が多いかは、次に書く記事の材料になる。
 */
(function () {
  if (typeof gtag !== "function") return;

  var body = document.body;
  var ctx = {
    kt_category: body.getAttribute("data-cat") || "",
    kt_area: body.getAttribute("data-area") || "",
    kt_page_type: body.getAttribute("data-ptype") || ""
  };

  function merge(extra) {
    var o = {}, k;
    for (k in ctx) o[k] = ctx[k];
    for (k in extra) o[k] = extra[k];
    return o;
  }

  /* 事業所カード内のリンクなら、その事業所名を拾う */
  function businessOf(el) {
    var card = el.closest ? el.closest(".card") : null;
    if (!card) return "";
    var h = card.querySelector("h3");
    if (!h) return "";
    var no = h.querySelector(".no");
    var name = h.textContent || "";
    if (no) name = name.replace(no.textContent, "");
    return name.trim();
  }

  function cardIndex(el) {
    var card = el.closest ? el.closest(".card") : null;
    if (!card) return 0;
    var cards = document.querySelectorAll(".card");
    for (var i = 0; i < cards.length; i++) if (cards[i] === card) return i + 1;
    return 0;
  }

  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    if (!a) return;
    var href = a.getAttribute("href") || "";

    if (href.indexOf("tel:") === 0) {
      gtag("event", "tel_tap", merge({
        kt_business: businessOf(a),
        kt_position: cardIndex(a),
        kt_tel: href.slice(4)
      }));
      return;
    }

    if (/^https?:\/\//.test(href) && a.hostname && a.hostname !== location.hostname) {
      gtag("event", "outbound_click", merge({
        kt_business: businessOf(a),
        kt_position: cardIndex(a),
        link_url: a.href,
        link_domain: a.hostname
      }));
    }
  }, true);

  /* FAQ は <details> なので、開いたときだけ送る */
  document.addEventListener("toggle", function (e) {
    var d = e.target;
    if (!d || d.tagName !== "DETAILS" || !d.open) return;
    var s = d.querySelector("summary");
    gtag("event", "faq_open", merge({ kt_question: s ? s.textContent.trim() : "" }));
  }, true);
})();
