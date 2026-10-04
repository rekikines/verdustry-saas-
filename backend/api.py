from app.modules.external_api.connectors.rest import RESTConnector 
from app.modules.external_api.mapping import extract_records, apply_mapping 
connector = RESTConnector( base_url="https://jsonplaceholder.typicode.com", auth_type="none", credentials={}, ) 
print("Connexion :", connector.test_connection("posts")) 
payload = connector.fetch_page("posts") 
print("Type de reponse :", type(payload)) 
records = extract_records(payload, "") 
print("Nombre d'enregistrements :", len(records)) 
mapped = apply_mapping(records, {"title": "Titre", "body": "Contenu"}) 
print(mapped[:2])