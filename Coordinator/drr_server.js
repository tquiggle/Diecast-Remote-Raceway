/*
 * Diecast Remote Raceway - Race Coordination Server
 *
 * The DRR Race Coordination Server is a Node.js HTTP server that coordinates the actions
 * of multiple racetracks in a circuit.
 *
 * Linux Installation:
 *
 *    % sudo apt install nodejs
 *    % npm install express async-barrier node-cron --save
 *
 * The DRR_Server implements the following service endpoints
 *
 *    /register         Register to participate in a race circuit
 *    /deregister       Deregister and stop participating in a race circuit
 *    /start            Synchronize the start of a race
 *    /results          Post local race results and collect global results
 *    /DRR              Root of binary download location
 *
 * each of which is described in their handler definitions below.
 *
 * Release Serving
 *
 *   In addition to coordinating races, the Coordinaton Server provides software artifacts
 *   so the Starting Gate and Finish Line can auto uptate to new releases.  The directory
 *   structure is as follows:
 *
 *      <path>/DRR/                                # Root directory of release artifacts
 *                 SG/                             # Subdirectory containing Startig Gate releases
 *                    version.txt                  # Text file containing version # of current release
 *                    starting-gate-YYMMDDVV.tgz   # Compressed tar file for specified release
 *                 FL/                             # Subdirectory containing Finish Line releases
 *                    version.txt                  # Text file containing version # of current release
 *                    finish-line-YYMMDDVV.bin     # Arduino binary file for specified release
 *
 * Running on Google Cloud Platform:
 *
 *   TODO: Provide instructions on how to run in GCP
 *         Notify other participants when a track times out and is removed from a circuit
 *
 */

/* Imports */
const express = require('express')
const bodyParser = require('body-parser')
const os = require('os')
const cron = require('node-cron')

/* Globals */
const makeAsyncBarrier = require('async-barrier')
const port = 1968 // The year Mattel introduced Hot Wheels to the market
const idleTimeoutMilliseconds = 60 * 60 * 1000
const hostname = os.hostname()
const defaultCircuit = 'DRR'

// File system path for the root of the release directory. Customize this as you see fit
const releases_root = '/home/htdocs/DRR'

var server = express() // Server object provided by the Express framework: https://expressjs.com/
var ipToCircuit = {} // Map of client IP address to registered circuit
var circuits = {} // Map of all active circuits

server.use(bodyParser.json())
server.use('/DRR', express.static(releases_root))

/* The following state is maintained for each circuit */
circuits[defaultCircuit] = {}
circuits[defaultCircuit].numParticipants = 0
circuits[defaultCircuit].participants = []
circuits[defaultCircuit].results = []
circuits[defaultCircuit].startBarrier = null
circuits[defaultCircuit].resultsBarrier = null
circuits[defaultCircuit].registerBarrier = null

/* Schedule a periodic task to run every minute looking for lost/disconnected tracks */
cron.schedule('* * * * *', function() {
    now = Date.now()
    for (circuit in circuits) {
        for (ip in circuits[circuit].participants) {
            if (now - circuits[circuit].participants[ip].lastRequestTime > idleTimeoutMilliseconds) {
                console.log(`ip ${ip} timed out from cicuit ${circuit}`)
                deregister(ip)
            }
        }
    }
})

/*
 * Remove regitration for ip
 */
function deregister(ip) {
    if (ip in ipToCircuit) {
        const circuit = ipToCircuit[ip]
        delete ipToCircuit[ip]
        const index = circuits[circuit].participants.indexOf(ip)
        if (index > -1) {
            circuits[circuit].participants.splice(index, 1)
            circuits[circuit].numParticipants--
            circuits[circuit].results = []
            circuits[circuit].startBarrier = makeAsyncBarrier(circuits[circuit].numParticipants)
            delete circuits[circuit].registerBarrier;
        } else {
            console.log(`ip ${ip} found in ipToCircuit, but not in circuit ${circuit}.participants`)
        }
    }
}

/*
 * Regitration ip in circuit based on registration information
 */
function register(ip, registration) {
    const circuit = 'circuit' in registration ? registration.circuit : defaultCircuit
    console.log(`registering ip ${ip} in circuit ${circuit}`)

    // Check to see if the registrant is already registered in a different circuit
    if (ip in ipToCircuit && ipToCircuit[ip] !== circuit) {
        console.log(`ip ${ip} registered in another circuit ${ipToCircuit[ip]}.  Deregistering`)
        deregister(ip)
    }

    if (!(circuit in circuits)) {
        console.log('creating new circuit ' + circuit + ' from registration')
        circuits[circuit] = {}
        circuits[circuit].numParticipants = 0
        circuits[circuit].participants = []
        circuits[circuit].results = []
    }

    if ((ip in circuits[circuit].participants)) {
        console.log(`ip ${ip} already registered in circuit ${circuit}`)
    } else {
        circuits[circuit].participants[ip] = {}
        circuits[circuit].numParticipants++
        circuits[circuit].joinBarrier = makeAsyncBarrier(2)
        circuits[circuit].startBarrier = makeAsyncBarrier(circuits[circuit].numParticipants)
    }

    const trackName = 'trackName' in registration ? registration.trackName :
        'Track ' + circuits[circuit].numParticipants
    circuits[circuit].participants[ip].trackName = trackName
    circuits[circuit].participants[ip].numLanes = registration.numLanes
    circuits[circuit].participants[ip].carIcons = registration.carIcons
    circuits[circuit].participants[ip].lastRequestTime = Date.now()
    ipToCircuit[ip] = circuit

    numParticipants = circuits[circuit].numParticipants
    if (numParticipants == 1) {
        /* This is the first registration in the circuit.  Create the barrier to syncronize registrations */
        console.log(`creating registrationBarrier for {circuit}`)
        circuits[circuit].registrationBarrier = makeAsyncBarrier(2)
    }

    console.log(`Registration complete, numParticipants: ${numParticipants}`)
    console.log("")

    return circuit

}

function sendErrorResponse(res, code, text) {
    res.writeHead(code, {
        'Content-Type': 'text/plain'
    })
    res.write(text)
    res.end()
}

/*
 * POST /register
 *
 * Accept registration from a track
 *
 * POST Body:
 *
 *   {"circuit": <string>,
 *    "trackName": <string>,
 *    "numLanes": <int>, 
 *    "carIcons": ["<car_1_icon_name>", "<car_2_icon_name>", ...]
 *   }
 *
 *   circuit:     (optional) Name of the circuit to join.
 *                           If absent, the caller will join the default "DRR" circuit
 *
 *   trackName:   (optional) Name of the track for use for display purposes. E.g.: "Gramps"
 *                           If absent, the trackName will be "Track #" where # is the number 
 *                           of tracks registered in the circuit including the current registration.
 *
 *   numLanes:               Number of lanes configured for the registering track.
 *                           Values can range of 1 to 4
 *
 *   carIcons:    (optional) An array of icon names that the user selected for the cars on their
 *                           local track.  This allows all participating tracks to display the same
 *                           icons on the race display for each track.  If not present, the local
 *                           track will use default icons for cars on remote track lanes.
 *
 *  Return:
 *
 *   The POST returns a JSON body with the registration data for each track in the circuit, excluding
 *   the track that originated the POST.  The shared circuit name is also omitted.
 *
 *   {"ip": <string>,
 *    "remoteRegistrations": [
 *       {"trackName": <string>,
 *        "numLanes": <int>,
 *        "carIcons": ["<car_1_icon_name>", "<car_2_icon_name>", ...],
 *       },
 *       <repeated for any additional tracks in the circuit>
 *      ]
 *    }
 */

server.post('/register', async function(req, res) {
    const ip = req.connection.remoteAddress
    let registration

    console.log(`/register(${ip}):`)
    console.log('req.body = ', req.body)

    let circuit = register(ip, req.body)

    await circuits[circuit].registrationBarrier()

    let results = {}
    results.ip = ip
    results.remoteRegistrations = []

    for (rip in circuits[circuit].participants) {
        if (rip != ip) {
            let registration = {}
            registration.trackName = circuits[circuit].participants[rip].trackName
            registration.numLanes = circuits[circuit].participants[rip].numLanes
            registration.carIcons = circuits[circuit].participants[rip].carIcons

            results.remoteRegistrations.push(registration)
        }
    }

    res.writeHead(200, {
        'Content-Type': 'application/json'
    })
    res.write(JSON.stringify(results))
    res.end()
    console.log("")
})

/*
 * GET /start 
 *
 *   Await start of race.
 *
 * Return:
 *
 *    200 Status Code
 *
 *    "Start the Race!"
 *
 */
server.get('/start', async function(req, res) {
    const ip = req.connection.remoteAddress

    console.log(`/start(${ip}:`)

    if (!(ip in ipToCircuit)) {
        sendErrorResponse(res, 424, 'Received /start request prior to registration')
        return
    }
    const circuit = ipToCircuit[ip]

    console.log(`/start(${ip}: waiting for race ready`)
    await circuits[circuit].startBarrier()
    console.log(`/start(${ip}: race is ready`)
    circuits[circuit].resultsBarrier = makeAsyncBarrier(circuits[circuit].numParticipants)
    circuits[circuit].results = []
    circuits[circuit].participants[ip].lastRequestTime = Date.now()

    res.writeHead(200, {
        'Content-Type': 'text/plain'
    })
    res.write("Start the Race!")
    res.end()
    console.log("")
})


/*
 * POST /results
 *
 *   Coordinate race results
 *
 * POST Body:
 *
 *   The POST body is a JSON array of lane results
 *   [
 *     {"laneNumber": <number>, "laneTime":<number>},
 *     ...
 *     {"laneNumber": <number>, "laneTime":<number>}
 *   ]
 *
 *  Return:
 *
 *   A sorted list of finishers from first to last
 *
 *   [
 *     {"trackName", "laneNumber": <number>, "laneTime":<number>},
 *     ...
 *     {"trackName", "laneNumber": <number>, "laneTime":<number>}
 *   ]
 *
 */

server.post('/results', async function(req, res) {
    const ip = req.connection.remoteAddress

    console.log(`/results(${ip}):`)
    console.log('req.body = ', req.body)

    if (!(ip in ipToCircuit)) {
        sendErrorResponse(res, 424, 'Received /results request prior to registration')
        return
    }

    const circuit = ipToCircuit[ip]
    const trackName = circuits[circuit].participants[ip].trackName

    for (index in req.body) {
        let result = req.body[index]
        result.trackName = trackName
        console.log('adding result to circuit', result)
        circuits[circuit].results.push(result)
    }

    // Wait for all results
    await circuits[circuit].resultsBarrier()
    circuits[circuit].startBarrier = makeAsyncBarrier(circuits[circuit].numParticipants)
    circuits[circuit].participants[ip].lastRequestTime = Date.now()

    sortedResults = circuits[circuit].results
    sortedResults.sort(function(a, b) {
        return a.laneTime - b.laneTime
    })

    console.log('sortedResults: ', sortedResults)

    res.writeHead(200, {
        'Content-Type': 'application/json'
    })
    res.write(JSON.stringify(sortedResults))
    res.end()
    console.log("")
})


/*
 * POST /deregister
 *
 *   Remove participant from circuit.
 *
 * POST Body:
 *
 *   [empty]
 *
 *  Return:
 *
 *    Goodbye message
 *
 */
server.post('/deregister', async function(req, res) {
    const ip = req.connection.remoteAddress

    console.log(`/deregister(${ip}):`)

    deregister(ip)
    res.writeHead(200, {
        'Content-Type': 'text/plain'
    })
    res.write('Deregistration complete. Bye.')
    res.end()
    console.log("")
})

/* Ladies and gentlemen, start your server! */
server.listen(port, () => console.log(`Raceway server listening at http://${hostname}:${port}`))

// vim: expandtab: sw=4
