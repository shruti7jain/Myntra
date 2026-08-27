from process_insights import classify_text_heuristically


def test_post_purchase_fit_complaint_is_noise():
    text = "Mene M size order kiya tha but ye bahut tight hai, size chart galat hai bilkul."
    result = classify_text_heuristically(text, "")
    assert result["theme"] == "unrelated_other", result


def test_wrong_product_return_service_is_noise():
    text = "WORST CUSTOMER SERVICE TEAM, delivered wrong product & on placing return request their investigation team fails to look into the case properly & cancel the return without keeping me posted. On speaking with customer service n their supervisor, none of them are able to help, all are giving silly same statements of helplessness. Not gonna place an order through myntra ever again."
    result = classify_text_heuristically(text, "")
    assert result["theme"] == "unrelated_other", result


def test_pre_purchase_sizing_hesitation_stays_in_scope():
    text = "I saved this dress but I'm not sure whether the size chart is accurate and the fit may be too tight."
    result = classify_text_heuristically(text, "")
    assert result["theme"] == "fit_sizing_anxiety", result


if __name__ == "__main__":
    test_post_purchase_fit_complaint_is_noise()
    test_wrong_product_return_service_is_noise()
    test_pre_purchase_sizing_hesitation_stays_in_scope()
    print("theme filter regression checks passed")
