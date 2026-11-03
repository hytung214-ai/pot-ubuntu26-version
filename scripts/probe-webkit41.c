/* Validate the actual supported C ABI and libsoup 3 ownership, not just .pc names. */
#include <webkit2/webkit2.h>
#include <jsc/jsc.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    void (*set_headers)(WebKitURISchemeResponse *, SoupMessageHeaders *) =
        webkit_uri_scheme_response_set_http_headers;
    SoupMessageHeaders *headers = soup_message_headers_new(SOUP_MESSAGE_HEADERS_RESPONSE);
    soup_message_headers_append(headers, "X-Pot-ABI", "libsoup3");
    if (strcmp(soup_message_headers_get_one(headers, "X-Pot-ABI"), "libsoup3")) return 1;
    GInputStream *stream = g_memory_input_stream_new_from_data("pot", 3, NULL);
    WebKitURISchemeResponse *response = webkit_uri_scheme_response_new(stream, 3);
    /* WebKit takes full ownership; keep one independent reference for this test. */
    set_headers(response, soup_message_headers_ref(headers));
    g_object_unref(response);
    g_object_unref(stream);
    soup_message_headers_unref(headers);
    SoupCookie *cookie = soup_cookie_new("pot", "abi", "localhost", "/", 60);
    if (!cookie) return 2;
    soup_cookie_free(cookie);
    printf("WebKitGTK %u.%u.%u; JavaScriptCore %u.%u.%u; libsoup %u.%u.%u: PASS\n",
           webkit_get_major_version(), webkit_get_minor_version(), webkit_get_micro_version(),
           jsc_get_major_version(), jsc_get_minor_version(), jsc_get_micro_version(),
           soup_get_major_version(), soup_get_minor_version(), soup_get_micro_version());
    return 0;
}
