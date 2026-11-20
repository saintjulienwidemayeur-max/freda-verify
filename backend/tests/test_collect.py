import io
import zipfile

from tests.conftest import PASSWORD, auth, first_org, register

JPG = b"\xff\xd8\xff\xe0" + b"VOLUNTEERPHOTO" * 8


def b(tok):
    return {"Authorization": f"Bearer {tok}"}


def setup(client, email="o@o.example", name="Org O"):
    t = register(client, email, name)
    org = first_org(client, t)
    c = client.post(f"/api/v1/organizations/{org['id']}/pad-campaigns", json={"name": "Pilot"}, headers=auth(t))
    assert c.status_code == 201, c.text
    camp = c.json()
    return t, org, camp, camp["url"].split("#c=")[1]


def start(client, ctok, **kw):
    return client.post("/api/v1/collect/start", json={"consent": True, "consent_version": "draft-1", **kw}, headers=b(ctok))


def put(client, ptok, kind, slot=1, light="indoor", data=JPG, ctype="image/jpeg"):
    return client.put(f"/api/v1/collect/samples/{kind}/{slot}?light={light}", content=data, headers={**b(ptok), "Content-Type": ctype})


def test_link_is_a_fragment_url_and_campaign_token_opens_nothing_else(client):
    t, org, camp, ctok = setup(client)
    assert camp["url"].endswith(f"/contribute#c={ctok}") and ctok.startswith("fvc_")
    assert client.get("/api/v1/collect/info", headers=b(ctok)).status_code == 200
    assert client.get(f"/api/v1/organizations/{org['id']}/pad-campaigns", headers=b(ctok)).status_code == 401      # the link is not a dashboard credential
    assert client.get("/api/v1/collect/info", headers=b("fvc_" + "x" * 30)).status_code == 401
    assert client.get("/api/v1/collect/info", headers=auth(t)).status_code == 401                                  # a dashboard JWT is not a campaign link


def test_consent_is_required_before_anything(client):
    _, _, _, ctok = setup(client)
    assert client.post("/api/v1/collect/start", json={"consent": False, "consent_version": "draft-1"}, headers=b(ctok)).status_code == 422
    assert client.post("/api/v1/collect/start", json={"consent": True, "consent_version": "old"}, headers=b(ctok)).status_code == 422
    assert client.put("/api/v1/collect/samples/live/1", content=JPG, headers={**b(ctok), "Content-Type": "image/jpeg"}).status_code == 401   # campaign token cannot upload
    r = start(client, ctok, skin_label="dark")
    assert r.status_code == 201 and r.json()["code"] == "p001" and r.json()["token"].startswith("fvp_")


def test_upload_rules_and_status(client):
    _, _, _, ctok = setup(client)
    ptok = start(client, ctok).json()["token"]
    assert put(client, ptok, "live", 1).status_code == 204
    assert put(client, ptok, "live", 1).status_code == 204                      # same slot replaces
    assert put(client, ptok, "print", 2, light="window").status_code == 204
    assert put(client, ptok, "face", 1).status_code == 404 and put(client, ptok, "live", 9).status_code == 404
    assert put(client, ptok, "live", 3, light="moon").status_code == 422
    assert put(client, ptok, "live", 3, data=b"<svg/>" + b" " * 64, ctype="image/svg+xml").status_code == 422
    assert client.get("/api/v1/collect/me", headers=b(ptok)).json()["samples"] == {"live": 1, "print": 1, "replay": 0, "mask": 0}
    assert client.post("/api/v1/collect/finish", headers=b(ptok)).status_code == 204


def test_owner_sees_counts_exports_decrypted_layout_and_audits(client):
    t, org, camp, ctok = setup(client)
    ptok = start(client, ctok, skin_label="light").json()["token"]
    put(client, ptok, "live", 1)
    put(client, ptok, "replay", 1, light="dim")
    row = client.get(f"/api/v1/organizations/{org['id']}/pad-campaigns", headers=auth(t)).json()[0]
    assert row["volunteers"] == 1 and row["samples"]["live"] == 1 and row["samples"]["replay"] == 1
    z = client.get(f"/api/v1/organizations/{org['id']}/pad-campaigns/{camp['id']}/export", headers=auth(t))
    assert z.status_code == 200 and z.headers["cache-control"] == "no-store"
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "genuine/p001_indoor_1.jpg" in names and "attack_replay/p001_dim_1.jpg" in names and "people.csv" in names
    assert zipfile.ZipFile(io.BytesIO(z.content)).read("genuine/p001_indoor_1.jpg") == JPG
    logs = client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()
    assert any(x["action"] == "pad_campaign.exported" for x in logs)


def test_volunteer_can_erase_everything_and_owner_can_delete_the_campaign(client):
    t, org, camp, ctok = setup(client)
    p1 = start(client, ctok).json()["token"]
    p2 = start(client, ctok).json()["token"]
    put(client, p1, "live", 1)
    put(client, p2, "live", 1)
    assert client.delete("/api/v1/collect/me", headers=b(p1)).status_code == 204
    assert client.get("/api/v1/collect/me", headers=b(p1)).status_code == 401
    row = client.get(f"/api/v1/organizations/{org['id']}/pad-campaigns", headers=auth(t)).json()[0]
    assert row["volunteers"] == 1 and row["samples"]["live"] == 1
    assert client.post(f"/api/v1/organizations/{org['id']}/pad-campaigns/{camp['id']}/active?active=false", headers=auth(t)).status_code == 200
    assert client.get("/api/v1/collect/info", headers=b(ctok)).status_code == 410
    assert client.delete(f"/api/v1/organizations/{org['id']}/pad-campaigns/{camp['id']}", headers=auth(t)).status_code == 204
    assert client.get("/api/v1/collect/me", headers=b(p2)).status_code == 401           # everything went with the campaign


def test_permissions_and_isolation(client):
    t, org, camp, ctok = setup(client)
    register(client, "m@m.example", "Org M")
    client.post(f"/api/v1/organizations/{org['id']}/members", json={"email": "m@m.example", "role": "member"}, headers=auth(t))
    mt = client.post("/api/v1/auth/login", json={"email": "m@m.example", "password": PASSWORD}).json()
    assert client.get(f"/api/v1/organizations/{org['id']}/pad-campaigns", headers=auth(mt)).status_code == 403
    other = register(client, "q@q.example", "Org Q")
    assert client.get(f"/api/v1/organizations/{org['id']}/pad-campaigns", headers=auth(other)).status_code == 404
    oorg = first_org(client, other)
    assert client.get(f"/api/v1/organizations/{oorg['id']}/pad-campaigns/{camp['id']}/export", headers=auth(other)).status_code == 404
