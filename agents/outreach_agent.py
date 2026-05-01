from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.models import CarPreferences, CarListing
from config import LLM_MODEL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
from config import SENDGRID_API_KEY, SENDGRID_FROM_EMAIL
import json


_DEALER_EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are writing on behalf of a professional car broker reaching out to a dealership. "
        "Be concise, professional, and show the buyer is qualified and ready to move quickly."
    )),
    ("human", (
        "Write a short professional email to {dealer_name} about the following listing:\n"
        "{year} {make} {model} — ${price:,} — {mileage:,} miles\n"
        "Listing: {listing_url}\n\n"
        "The broker represents a qualified buyer with a budget of ${price_min:,}–${price_max:,} "
        "looking for this exact vehicle near {location}. "
        "The broker's name is {broker_name}, email {broker_email}, phone {broker_phone}.\n\n"
        "Ask: confirm availability, best out-the-door price, and invite a callback. "
        "Keep it under 150 words. No HTML."
    )),
])

_DEALER_SMS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Write a professional SMS under 300 characters from a car broker to a dealership."),
    ("human", (
        "Broker {broker_name} has a buyer for your {year} {make} {model} (${price:,}). "
        "Is it still available? Best OTD price? Reply or call {broker_phone}."
    )),
])

_EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert automotive assistant writing a personalized car search results email. Be professional, clear, and helpful."),
    ("human", (
        "Write an HTML email body for these top car listings found for {name}.\n"
        "Preferences: {make} {model}, budget ${price_min:,}-${price_max:,}, near {location}.\n\n"
        "Top listings:\n{listings_json}\n\n"
        "Include: greeting, listing summaries (price, mileage, color, dealer, link), and a call to action."
    )),
])

_SMS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Write a concise SMS under 300 characters. Include top 1-3 cars with price and mileage. End with a call to action."),
    ("human", (
        "SMS summary for {make} {model} search near {location}:\n{listings_json}"
    )),
])


def generate_email_content(prefs: CarPreferences, listings: list[CarListing], critic_feedback: str = None) -> str:
    from agents.rag_agent import is_rag_available, query_car_specs

    car_context = ""
    if is_rag_available():
        specs = query_car_specs(prefs.make, prefs.model, n_results=2)
        if specs:
            car_context = "\n".join(specs)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.4)
    car_context_line = (
        f"\nUse these verified facts about the {prefs.make} {prefs.model} to enrich the email:\n{car_context}\n"
        if car_context else ""
    )
    if critic_feedback or car_context:
        human_msg = (
            "Write an HTML email body for these top car listings found for {name}.\n"
            "Preferences: {make} {model}, budget ${price_min:,}-${price_max:,}, near {location}."
            + car_context_line +
            "\nTop listings:\n{listings_json}\n\n"
            "Include: greeting, listing summaries (price, mileage, color, dealer, link), and a call to action."
        )
        if critic_feedback:
            human_msg += f"\n\nCritic feedback to incorporate:\n{critic_feedback}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert automotive assistant writing a personalized car search results email. Be professional, clear, and helpful."),
            ("human", human_msg),
        ])
    else:
        prompt = _EMAIL_PROMPT
    chain = prompt | llm | StrOutputParser()
    listings_data = [l.model_dump() for l in listings]
    return chain.invoke({
        "name": prefs.user_email or "Car Buyer",
        "make": prefs.make,
        "model": prefs.model,
        "price_min": prefs.price_min,
        "price_max": prefs.price_max,
        "location": prefs.location,
        "listings_json": json.dumps(listings_data, indent=2),
    })


def generate_sms_content(prefs: CarPreferences, listings: list[CarListing], critic_feedback: str = None) -> str:
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)
    if critic_feedback:
        human_msg = (
            "SMS summary for {make} {model} search near {location}:\n{listings_json}\n\n"
            f"Critic feedback to incorporate:\n{critic_feedback}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Write a concise SMS under 300 characters. Include top 1-3 cars with price and mileage. End with a call to action."),
            ("human", human_msg),
        ])
    else:
        prompt = _SMS_PROMPT
    chain = prompt | llm | StrOutputParser()
    top3 = [l.model_dump() for l in listings[:3]]
    return chain.invoke({
        "make": prefs.make,
        "model": prefs.model,
        "location": prefs.location,
        "listings_json": json.dumps(top3, indent=2),
    })


def send_sms(to_number: str, message: str) -> dict:
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number,
        )
        return {"success": True, "sid": msg.sid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_email(to_email: str, subject: str, html_body: str) -> dict:
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        mail = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
        )
        response = sg.send(mail)
        return {"success": True, "status": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_dealer_outreach(prefs: CarPreferences, listings: list[CarListing]) -> list[dict]:
    """Generate (and optionally send) outreach to the selling dealer for each top listing."""
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)
    broker_name = prefs.broker_name or "Your Agent"
    broker_email = prefs.broker_email or ""
    broker_phone = prefs.broker_phone or ""

    results = []
    for listing in listings[:3]:  # contact top 3 dealers only
        dealer_label = listing.dealer_name or "Dealer"
        try:
            email_chain = _DEALER_EMAIL_PROMPT | llm | StrOutputParser()
            email_body = email_chain.invoke({
                "dealer_name": dealer_label,
                "year": listing.year,
                "make": prefs.make,
                "model": prefs.model,
                "price": listing.price,
                "mileage": listing.mileage,
                "listing_url": listing.listing_url or "N/A",
                "price_min": prefs.price_min,
                "price_max": prefs.price_max,
                "location": prefs.location,
                "broker_name": broker_name,
                "broker_email": broker_email,
                "broker_phone": broker_phone,
            })

            sms_chain = _DEALER_SMS_PROMPT | llm | StrOutputParser()
            sms_body = sms_chain.invoke({
                "broker_name": broker_name,
                "year": listing.year,
                "make": prefs.make,
                "model": prefs.model,
                "price": listing.price,
                "broker_phone": broker_phone,
            })

            entry = {
                "dealer_name": dealer_label,
                "dealer_phone": listing.dealer_phone,
                "dealer_email": listing.dealer_email,
                "listing_title": listing.title,
                "listing_url": listing.listing_url,
                "email_content": email_body,
                "sms_content": sms_body,
                "email_sent": None,
                "sms_sent": None,
            }

            # Send if dealer contact info is available
            if listing.dealer_email:
                subject = f"Qualified Buyer Inquiry — {listing.year} {prefs.make} {prefs.model}"
                entry["email_sent"] = send_email(listing.dealer_email, subject, f"<pre>{email_body}</pre>")

            if listing.dealer_phone and prefs.broker_phone:
                entry["sms_sent"] = send_sms(listing.dealer_phone, sms_body)

        except Exception as e:
            entry = {
                "dealer_name": dealer_label,
                "error": str(e),
                "email_content": "",
                "sms_content": "",
            }

        results.append(entry)

    return results


def run_outreach_agent(prefs: CarPreferences, listings: list[CarListing], critic_feedback: str = None) -> dict:
    results = {}

    if prefs.delivery_email and prefs.user_email:
        email_body = generate_email_content(prefs, listings, critic_feedback=critic_feedback)
        subject = f"Your {prefs.make} {prefs.model} Results - Top {len(listings)} Picks"
        results["email"] = send_email(prefs.user_email, subject, email_body)
        results["email_content"] = email_body

    if prefs.delivery_sms and prefs.user_phone:
        sms_body = generate_sms_content(prefs, listings, critic_feedback=critic_feedback)
        results["sms"] = send_sms(prefs.user_phone, sms_body)
        results["sms_content"] = sms_body

    return results
