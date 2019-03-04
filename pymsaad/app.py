import flask
import adal
import requests
import os

from pymsaad.cfg import reg_info, SECRET_KEY, CERT_PEM_ABS_PATH, KEY_PEM_ABS_PATH
from pymsaad.util import get_rand_hex, save_token, VersionError

########################################################################################################################
# SET UP SOMEWHERE TO PUT THE TOKEN.  ##################################################################################
HOME_FOLDER = os.path.expanduser('~')
# This block will ensure SAVE_FOLDER is only 1 folder deeper than an existing folder...
if os.path.exists(os.path.join(HOME_FOLDER, 'Documents')):
    SAVE_FOLDER = os.path.join(HOME_FOLDER, 'Documents', 'AAD Tokens')
else:
    SAVE_FOLDER = os.path.join(HOME_FOLDER, 'AAD Tokens')
# ...which makes this simple statement ok, otherwise we'd need: os.makedirs().
if not os.path.exists(SAVE_FOLDER):
    os.mkdir(SAVE_FOLDER)
    print('INFO: {fold} directory not found. Created {fold} directory.'.format(fold=SAVE_FOLDER))
# Sanity:
assert os.path.exists(SAVE_FOLDER)
########################################################################################################################


########################################################################################################################
# SET UP FLASK AND GLOBALS.  ###########################################################################################
app = flask.Flask(__name__)
app.config.from_object(__name__)
app.secret_key = SECRET_KEY

PORT = 5000
API_VERSION = 'v1.0'
# reg_info['state'] will give a
STATE = reg_info['state']


AUTHORITY_URL = reg_info['authority_host_url'] + '/' + reg_info['tenant'] + '/' + 'oauth2/authorize?'
SHORT_AUTH_URL = reg_info['authority_host_url'] + '/' + reg_info['tenant']
TEMPLATE_AUTH_PARAM_STRING_V1 = 'response_type=code&client_id={}&redirect_uri={}&' + 'state={}&resource={}'
TEMPLATE_AUTH_PARAM_STRING_V2 = 'response_type=code&client_id={}&redirect_uri={}&' + 'state={}&scope={}'

########################################################################################################################



########################################################################################################################
# WEB APP:  ############################################################################################################
@app.route("/")
def main():
    login_url = 'http://localhost:{}/login'.format(PORT)
    resp = flask.Response(status=307)
    resp.headers['location'] = login_url
    return resp

@app.route("/login")
def login():
    flask.session['state'] = STATE
    # modify vars for switching b/w v1.0 endpoint and v2.0 endpoint.
    if API_VERSION == "v1.0":
        _template_param_string = TEMPLATE_AUTH_PARAM_STRING_V1
        _stuff_to_get = reg_info['resource']
    elif API_VERSION == 'v2.0':
        _template_param_string = TEMPLATE_AUTH_PARAM_STRING_V2
        _stuff_to_get = reg_info['scope']
    else:
        raise VersionError('Please Specify either "v1.0" or "v2.0" for the API_VERSION var.')
    # Build the full auth URL. Assembling manually so do NOT use plaintext vals.
    params = _template_param_string.format(
        reg_info['client_id'],
        reg_info['redirect_uri'],
        STATE,
        _stuff_to_get
    )
    auth_url = AUTHORITY_URL + params
    resp = flask.Response(status=307)
    resp.headers['location'] = auth_url
    return resp

@app.route("/getAToken")
def main_logic():
    code = flask.request.args['code']
    state = flask.request.args['state']
    if state != flask.session['state']:
        raise ValueError("State does not match")
    auth_context = adal.AuthenticationContext(SHORT_AUTH_URL, api_version=None)
    token_response = auth_context.acquire_token_with_authorization_code(
        code,
        reg_info['redirect_uri_plaintext'],
        reg_info['resource_plaintext'],
        reg_info['client_id'],
        client_secret=reg_info['secret']
    )
    # It is recommended to save this when using a production app...
    flask.session['access_token'] = token_response['accessToken']

    token_file_pth = os.path.join(SAVE_FOLDER, 'AAD Token.txt')
    if os.path.exists(token_file_pth):
        print('{} ALREADY EXISTS. OVERWRITING.'.format(token_file_pth))
    # ...so we don't get a new one every time we open the browser.
    if save_token(flask.session.get('access_token'), token_file_pth):
        print('SUCCESS. Your access token is here: {}'.format(token_file_pth))
    else:
        print('FAILED TO SAVE TOKEN FILE HERE: {}'.format(token_file_pth))

    return flask.redirect('/graphcall')

@app.route('/graphcall')
def graphcall():
    if 'access_token' not in flask.session:
        return flask.redirect(flask.url_for('login'))
    company_name = reg_info['tenant'].split('.')[0]
    endpoint = reg_info['resource_plaintext'] + '/' + API_VERSION + '/me/'
    http_headers = {'Authorization': flask.session.get('access_token'),
                    'User-Agent': '{}-adal-partnercenter'.format(company_name),
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'client-request-id': get_rand_hex(10)}
    graph_data = requests.get(endpoint, headers=http_headers, stream=False).json()
    return flask.render_template('display_graph_info.html', graph_data=graph_data)
########################################################################################################################

########################################################################################################################
# lOCAL SSL:  ##########################################################################################################
if __name__ == "__main__":
    cert, key = CERT_PEM_ABS_PATH, KEY_PEM_ABS_PATH
    app.run(ssl_context=(cert, key))
########################################################################################################################