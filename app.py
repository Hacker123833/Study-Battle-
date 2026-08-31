
# ULTIMATE MULTIPLAYER FEATURES
MAX_PLAYERS = 15
QUESTION_COUNTS = [5, 10, 15, 20, 30]
ULTIMATE_FEATURES = {
    "host_controls": True,
    "live_leaderboard": True,
    "chat_reactions": True,
    "team_battles": True,
    "boss_battle": True,
    "battle_statistics": True,
    "rematch": True,
    "achievements": True,
    "daily_missions": True,
    "mvp_titles": True,
    "champion_crown": True,
    "win_streak_rewards": True,
    "battle_coins": True,
    "player_levels": True,
    "hall_of_fame": True,
    "winner_choice": True,
}

from flask import Flask, request, jsonify, render_template_string
import random, string, threading, time, json, os, hashlib, secrets, re, copy
app = Flask(__name__)
PORT = int(os.environ.get("PORT", 5000))
SAVE_FILE = "studybattle_progress.json"
MAX_PLAYERS = 15
MIN_PLAYERS = 2
QUESTION_TIME = 15
BASE_POINTS = 5
lock = threading.Lock()
rooms = {}

# Strong topic-based question randomization: questions are dealt from a shuffled
# deck and are not repeated until the available pool for that selection is exhausted.
QUESTION_DECKS = {}
QUESTION_DECK_LOCK = threading.Lock()

# Testing accounts are kept in the database but never shown on Hall of Fame.
HALL_OF_FAME_HIDDEN_NAMES = {"test", "test 1", "test1", "jordan"}
players = {}

DARE_LIST = [
    'Do your funniest walk for 20 seconds.', 'Pretend you are a news reporter for 30 seconds.', 
    'Speak like a robot for 30 seconds.', 'Do 5 funny poses.', 'Pretend to be a teacher for 30 seconds.', 
    'Give a dramatic speech about why you lost.', 'Act like a chicken for 20 seconds.', 
    'Make your funniest serious face.', 'Do a victory dance even though you came last.', 
    'Introduce yourself like a celebrity.', 'Say three tongue twisters.', 'Pretend to be a sports commentator.', 
    'Walk like a penguin for 20 seconds.', 'Make up a funny slogan for StudyBattle.', 
    'Pretend to answer an imaginary phone call.', 'Do your best superhero pose.', 
    'Give everyone a dramatic thumbs-up.', 'Pretend you just won a million rupees.', 
    'Act like a confused tourist for 20 seconds.', 'Pretend you are presenting breaking news.', 
    'Say your name in three different funny voices.', 'Pretend to be an NPC for 30 seconds.', 
    'Give a dramatic explanation of why your score is low.', 'Do a slow-motion celebration.', 
    'Pretend you are a game-show host.', 'Make up a two-line funny poem.', 
    'Pretend you are stuck in an invisible box.', 'Do your best statue impression.', 
    'Say a sentence like a movie villain.', 'Pretend you are giving a motivational speech.', 
    'Make a funny face for five seconds.', 'Pretend you are a football commentator.', 
    'Walk three steps like a cartoon character.', 'Pretend you are accepting an award.', 
    'Give yourself a ridiculous nickname.', "Say 'I will study harder' dramatically.", 
    'Pretend you are announcing a school assembly.', 'Do a tiny celebration dance.', 
    'Pretend you are an alien visiting Earth.', 'Describe your day like a documentary narrator.', 
    'Pretend you are selling an imaginary product.', 'Give a dramatic slow clap.', 
    'Pretend you are a weather reporter.', 'Say one sentence in an extremely dramatic voice.', 
    'Create a funny handshake with another player.', 'Pretend you are a very confused professor.', 
    'Do a 10-second invisible guitar solo.', 'Give a dramatic acceptance speech for coming last.', 
    'Pretend your pencil is a microphone and host a concert.', 'Pretend you are announcing the final score of a World Cup.'
]

QUESTIONS = [{'id': 'fluid_01',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'A substance that can flow is called a:',
  'options': ['Fluid', 'Solid', 'Crystal', 'Rigid body'],
  'answer': 0},
 {'id': 'fluid_02',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'The shear modulus of an ideal fluid is:',
  'options': ['Zero', 'Infinite', 'One', 'Negative'],
  'answer': 0},
 {'id': 'fluid_03',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'An ideal fluid is considered:',
  'options': ['Incompressible', 'Highly compressible', 'Highly viscous', 'Turbulent'],
  'answer': 0},
 {'id': 'fluid_04',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'An ideal fluid has:',
  'options': ['No internal friction', 'Maximum internal friction', 'Only turbulent flow', 'Zero density'],
  'answer': 0},
 {'id': 'fluid_05',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'In steady flow, velocity at each point is:',
  'options': ['Constant with time', 'Always zero', 'Always increasing', 'Random'],
  'answer': 0},
 {'id': 'fluid_06',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Surface tension makes a liquid surface tend to:',
  'options': ['Contract its area', 'Expand indefinitely', 'Lose all molecules', 'Become solid'],
  'answer': 0},
 {'id': 'fluid_07',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'A water spider walking on water is an example related to:',
  'options': ['Surface tension', 'Buoyancy only', 'Elasticity', 'Electricity'],
  'answer': 0},
 {'id': 'fluid_08',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Attraction between molecules of the same substance is:',
  'options': ['Cohesive force', 'Adhesive force', 'Buoyant force', 'Nuclear force'],
  'answer': 0},
 {'id': 'fluid_09',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Attraction between molecules of different substances is:',
  'options': ['Adhesive force', 'Cohesive force', 'Magnetic force', 'Gravitational force'],
  'answer': 0},
 {'id': 'fluid_10',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Maximum distance up to which molecular force is effective is:',
  'options': ['Range of molecular force', 'Critical velocity', 'Terminal distance', 'Flow length'],
  'answer': 0},
 {'id': 'fluid_11',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Imaginary sphere within which intermolecular force acts is the:',
  'options': ['Sphere of influence', 'Flow tube', 'Pressure shell', 'Capillary sphere'],
  'answer': 0},
 {'id': 'fluid_12',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Surface layer whose thickness equals the range of intermolecular force is:',
  'options': ['Surface film', 'Flow tube', 'Gas layer', 'Pressure layer'],
  'answer': 0},
 {'id': 'fluid_13',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Surface tension is tangential force per unit:',
  'options': ['Length', 'Area', 'Volume', 'Mass'],
  'answer': 0},
 {'id': 'fluid_14',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'SI unit of surface tension is:',
  'options': ['N/m', 'N/m2', 'J', 'Pa m'],
  'answer': 0},
 {'id': 'fluid_15',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'SI unit of surface energy is:',
  'options': ['Joule', 'Newton', 'Pascal', 'Watt'],
  'answer': 0},
 {'id': 'fluid_16',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Surface energy is stored as potential energy mainly in the:',
  'options': ['Surface layer', 'Centre of liquid', 'Container', 'Gas only'],
  'answer': 0},
 {'id': 'fluid_17',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Relation between surface tension and surface energy per unit area is:',
  'options': ['T = dW/dA', 'T = WdA', 'T = A/dW', 'T = dA/dW'],
  'answer': 0},
 {'id': 'fluid_18',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Angle of contact is measured at the:',
  'options': ['Point of contact', 'Centre of container', 'Bottom of liquid', 'Top of capillary only'],
  'answer': 0},
 {'id': 'fluid_19',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'An acute contact angle generally means the liquid:',
  'options': ['Partially wets the solid', 'Does not wet the solid', 'Has zero density', 'Has zero surface tension'],
  'answer': 0},
 {'id': 'fluid_20',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'An obtuse contact angle generally means the liquid:',
  'options': ['Does not wet the solid', 'Completely wets the solid', 'Always evaporates', 'Has zero viscosity'],
  'answer': 0},
 {'id': 'fluid_21',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'For zero contact angle, the notes state that the liquid:',
  'options': ['Completely wets the solid', 'Never wets the solid', 'Forms a convex meniscus', 'Has no molecular forces'],
  'answer': 0},
 {'id': 'fluid_22',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'An acute contact angle generally produces a:',
  'options': ['Concave meniscus', 'Convex meniscus', 'No surface', 'Flat solid'],
  'answer': 0},
 {'id': 'fluid_23',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'An obtuse contact angle generally produces a:',
  'options': ['Convex meniscus', 'Concave meniscus', 'No meniscus always', 'Spherical solid'],
  'answer': 0},
 {'id': 'fluid_24',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Angle of contact depends on the:',
  'options': ['Nature of liquid and solid in contact', 'Colour of liquid', 'Shape of room', 'Mass of Earth only'],
  'answer': 0},
 {'id': 'fluid_25',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'As temperature generally increases, surface tension:',
  'options': ['Decreases', 'Always increases', 'Becomes infinite', 'Never changes'],
  'answer': 0},
 {'id': 'fluid_26',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'A soluble impurity that increases cohesive force generally:',
  'options': ['Increases surface tension', 'Removes viscosity', 'Stops flow', 'Makes density zero'],
  'answer': 0},
 {'id': 'fluid_27',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Detergent is described in the notes as a substance that can:',
  'options': ['Decrease surface tension', 'Make surface tension infinite', 'Remove gravity', 'Increase mass'],
  'answer': 0},
 {'id': 'fluid_28',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Excess pressure inside a spherical liquid drop is:',
  'options': ['2T/r', '4T/r', 'T/r2', 'r/2T'],
  'answer': 0},
 {'id': 'fluid_29',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Excess pressure inside a soap bubble is:',
  'options': ['4T/r', '2T/r', 'T/4r', 'r/4T'],
  'answer': 0},
 {'id': 'fluid_30',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'A capillary tube has a very:',
  'options': ['Fine bore diameter', 'Large mass', 'Thick wall only', 'High temperature'],
  'answer': 0},
 {'id': 'fluid_31',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Rise or fall of a liquid in a capillary tube is:',
  'options': ['Capillary action', 'Diffusion', 'Radiation', 'Conduction'],
  'answer': 0},
 {'id': 'fluid_32',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Oil rising up a lamp wick is an example of:',
  'options': ['Capillary action', 'Turbulent flow', 'Elasticity', 'Buoyancy only'],
  'answer': 0},
 {'id': 'fluid_33',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'The capillary-height relation in the notes is:',
  'options': ['h = 2T cosθ/(ρgr)', 'h = ρgr/(2T cosθ)', 'h = 2ρgr/T', 'h = Tρgr'],
  'answer': 0},
 {'id': 'fluid_34',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'If cosθ is positive, capillary height h is:',
  'options': ['Positive/rise', 'Negative/fall', 'Always zero', 'Infinite'],
  'answer': 0},
 {'id': 'fluid_35',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'If cosθ is negative, capillary height h is:',
  'options': ['Negative/fall', 'Positive/rise', 'Always zero', 'Infinite'],
  'answer': 0},
 {'id': 'fluid_36',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Viscosity is the property by which relative motion between fluid layers experiences:',
  'options': ['Viscous drag', 'No force', 'Only gravity', 'Electrical attraction'],
  'answer': 0},
 {'id': 'fluid_37',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': "Newton's law of viscosity relates viscous force to area and:",
  'options': ['Velocity gradient', 'Density only', 'Temperature only', 'Volume'],
  'answer': 0},
 {'id': 'fluid_38',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'SI unit of coefficient of viscosity is:',
  'options': ['N s/m2', 'N/m', 'J', 'Pa m'],
  'answer': 0},
 {'id': 'fluid_39',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Hydrodynamics studies:',
  'options': ['Properties of fluids in motion', 'Only solids at rest', 'Electric charges', 'Light only'],
  'answer': 0},
 {'id': 'fluid_40',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'In laminar flow, adjacent layers move:',
  'options': ['Smoothly over each other', 'Randomly in all directions', 'Only vertically', 'With infinite velocity'],
  'answer': 0},
 {'id': 'fluid_41',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'In turbulent flow, velocity is generally:',
  'options': ['Changing and irregular', 'Constant everywhere', 'Always zero', 'Always negative'],
  'answer': 0},
 {'id': 'fluid_42',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Two streamlines in laminar flow:',
  'options': ['Never intersect', 'Always intersect', 'Have no direction', 'Become circles'],
  'answer': 0},
 {'id': 'fluid_43',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Velocity at which laminar flow becomes turbulent is:',
  'options': ['Critical velocity', 'Terminal velocity', 'Escape velocity', 'Angular velocity'],
  'answer': 0},
 {'id': 'fluid_44',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Reynolds number is:',
  'options': ['Dimensionless', 'Measured in newtons', 'Measured in joules', 'Measured in pascals'],
  'answer': 0},
 {'id': 'fluid_45',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'According to the supplied notes, Reynolds number below 1000 indicates:',
  'options': ['Streamline/laminar flow', 'Turbulent flow', 'No flow', 'Only capillary flow'],
  'answer': 0},
 {'id': 'fluid_46',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'According to the supplied notes, Reynolds number above 2000 indicates:',
  'options': ['Turbulent flow', 'Laminar flow', 'No viscosity', 'Zero density'],
  'answer': 0},
 {'id': 'fluid_47',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': "Stokes' law gives viscous force on a small sphere as:",
  'options': ['6πηrv', '2T/r', 'ρgh', 'mg/r'],
  'answer': 0},
 {'id': 'fluid_48',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'At terminal velocity, net force on the falling object is:',
  'options': ['Zero', 'Maximum', 'Infinite', 'Negative infinity'],
  'answer': 0},
 {'id': 'fluid_49',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'At terminal velocity, weight is balanced by:',
  'options': ['Viscous force plus buoyant force', 'Only gravity', 'Only surface tension', 'Only pressure'],
  'answer': 0},
 {'id': 'fluid_50',
  'subject': 'Physics',
  'topic': 'Mechanical Properties of Fluids',
  'q': 'Terminal velocity from the supplied notes is proportional to:',
  'options': ['r²(ρ1-ρ2)g/η', 'η/(r²ρg)', 'r/η only', 'ηr² only'],
  'answer': 0},
 {'id': 'current_electricity_01',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s laws are mainly used to solve electrical circuits containing several:',
  'options': ['Branches and loops', 'Only batteries', 'Only capacitors', 'Only wires'],
  'answer': 0},
 {'id': 'current_electricity_02',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s first law is also called the:',
  'options': ['Junction law or current law', 'Voltage law only', 'Loop resistance law', 'Bridge law'],
  'answer': 0},
 {'id': 'current_electricity_03',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'According to Kirchhoff’s first law, total current entering a junction is:',
  'options': ['Equal to total current leaving it',
              'Always greater than current leaving',
              'Always less than current leaving',
              'Zero in every circuit'],
  'answer': 0},
 {'id': 'current_electricity_04',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s first law is based on conservation of:',
  'options': ['Charge', 'Mass only', 'Energy only', 'Momentum'],
  'answer': 0},
 {'id': 'current_electricity_05',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'At a junction, charge cannot continuously:',
  'options': ['Accumulate', 'Move', 'Exist', 'Be measured'],
  'answer': 0},
 {'id': 'current_electricity_06',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The algebraic sum of currents at a junction is:',
  'options': ['Zero', 'One', 'Infinite', 'Equal to resistance'],
  'answer': 0},
 {'id': 'current_electricity_07',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s second law is also called the:',
  'options': ['Voltage law or loop law', 'Junction law', 'Current law only', 'Bridge law'],
  'answer': 0},
 {'id': 'current_electricity_08',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s second law applies to a:',
  'options': ['Closed loop', 'Single isolated point only', 'Open switch only', 'Single resistor only'],
  'answer': 0},
 {'id': 'current_electricity_09',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s second law states that the algebraic sum of potential differences and emfs in a closed loop is:',
  'options': ['Zero', 'Equal to current', 'Equal to resistance', 'Infinite'],
  'answer': 0},
 {'id': 'current_electricity_10',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In Kirchhoff’s loop law, potential differences may include products of:',
  'options': ['Current and resistance', 'Charge and time', 'Mass and velocity', 'Length and area'],
  'answer': 0},
 {'id': 'current_electricity_11',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'When loop tracing goes from the negative terminal to the positive terminal of a cell, the emf is taken as:',
  'options': ['Positive', 'Negative', 'Zero', 'Infinite'],
  'answer': 0},
 {'id': 'current_electricity_12',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'When loop tracing goes from the positive terminal to the negative terminal of a cell, the emf is taken as:',
  'options': ['Negative', 'Positive', 'Always zero', 'Infinite'],
  'answer': 0},
 {'id': 'current_electricity_13',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'If the loop-tracing direction is opposite to the assumed current direction, the IR term is written with:',
  'options': ['The opposite sign according to the convention', 'No sign', 'Only a positive sign', 'Only a negative sign'],
  'answer': 0},
 {'id': 'current_electricity_14',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The first step in solving a circuit using Kirchhoff’s laws is to:',
  'options': ['Choose directions of currents in different branches',
              'Remove all resistors',
              'Disconnect the battery',
              'Find the null point'],
  'answer': 0},
 {'id': 'current_electricity_15',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'While solving a circuit by Kirchhoff’s laws, one should use the:',
  'options': ['Minimum number of independent current variables possible',
              'Maximum number of variables possible',
              'Same current in every branch',
              'No current variables'],
  'answer': 0},
 {'id': 'current_electricity_16',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'After choosing current directions, Kirchhoff’s procedure requires applying the:',
  'options': ['Junction law', 'Only Ohm’s law', 'Only bridge law', 'Only surface-tension law'],
  'answer': 0},
 {'id': 'current_electricity_17',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s procedure next requires applying the voltage law to:',
  'options': ['Independent closed loops', 'Only open branches', 'Only junctions', 'Only batteries'],
  'answer': 0},
 {'id': 'current_electricity_18',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'After forming Kirchhoff equations, the equations are solved as:',
  'options': ['Simultaneous equations', 'A single definition', 'A graphical drawing only', 'A measurement only'],
  'answer': 0},
 {'id': 'current_electricity_19',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'If a calculated current is negative, it means the actual current direction is:',
  'options': ['Opposite to the initially assumed direction', 'Zero', 'Always larger', 'Along the battery only'],
  'answer': 0},
 {'id': 'current_electricity_20',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Kirchhoff’s laws can be applied to circuits containing multiple:',
  'options': ['Cells, resistors and branches', 'Only resistors', 'Only cells', 'Only galvanometers'],
  'answer': 0},
 {'id': 'current_electricity_21',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Wheatstone’s bridge is a network used for:',
  'options': ['Comparing resistances and determining an unknown resistance',
              'Measuring temperature only',
              'Generating emf',
              'Measuring mass'],
  'answer': 0},
 {'id': 'current_electricity_22',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A Wheatstone bridge works on the principle of a:',
  'options': ['Balanced bridge', 'Moving coil', 'Thermal expansion', 'Magnetic field'],
  'answer': 0},
 {'id': 'current_electricity_23',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'At balance in a Wheatstone bridge, current through the galvanometer is:',
  'options': ['Zero', 'Maximum', 'Infinite', 'Always negative'],
  'answer': 0},
 {'id': 'current_electricity_24',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'At balance, the two points connected to the galvanometer are at:',
  'options': ['The same potential', 'Different potentials always', 'Zero current but unequal potential', 'Infinite potential'],
  'answer': 0},
 {'id': 'current_electricity_25',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'At balance, a Wheatstone bridge is in an:',
  'options': ['Equipotential condition', 'Insulated condition', 'Unstable condition', 'Open-loop condition'],
  'answer': 0},
 {'id': 'current_electricity_26',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'For four resistances P, Q, R and S, the balance condition given in the material is:',
  'options': ['P/Q = R/S', 'P+Q=R+S', 'P/R=Q+S', 'P-S=Q-R'],
  'answer': 0},
 {'id': 'current_electricity_27',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The equivalent cross-multiplied Wheatstone balance condition is:',
  'options': ['P×S = Q×R', 'P×Q = R+S', 'P+S = Q×R', 'P/R = Q×S'],
  'answer': 0},
 {'id': 'current_electricity_28',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'When the Wheatstone bridge is balanced, the galvanometer junctions have:',
  'options': ['Equal potential', 'Equal resistance only', 'Equal current only', 'Zero resistance'],
  'answer': 0},
 {'id': 'current_electricity_29',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'One use of a Wheatstone bridge is to determine:',
  'options': ['An unknown resistance', 'Only current', 'Only voltage', 'Only power'],
  'answer': 0},
 {'id': 'current_electricity_30',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A Wheatstone bridge can also be used to:',
  'options': ['Compare resistances', 'Produce a magnetic field', 'Measure mass', 'Measure time'],
  'answer': 0},
 {'id': 'current_electricity_31',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'According to the material, a Wheatstone bridge can measure:',
  'options': ['Small changes in resistance', 'Only very large currents', 'Only temperature', 'Only capacitance'],
  'answer': 0},
 {'id': 'current_electricity_32',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Resistance-sensitive devices such as strain gauges are based on the:',
  'options': ['Wheatstone bridge principle', 'Kirchhoff first law only', 'Meter scale only', 'Jockey principle'],
  'answer': 0},
 {'id': 'current_electricity_33',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A meter bridge is a practical form of a:',
  'options': ['Wheatstone bridge', 'Galvanometer', 'Rheostat', 'Battery'],
  'answer': 0},
 {'id': 'current_electricity_34',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The resistance wire of a meter bridge is:',
  'options': ['One metre long and uniform', 'Ten metres long and non-uniform', 'One centimetre long', 'Infinitely long'],
  'answer': 0},
 {'id': 'current_electricity_35',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The meter-bridge wire is stretched along a:',
  'options': ['Metre scale', 'Voltmeter scale', 'Thermometer', 'Galvanometer scale'],
  'answer': 0},
 {'id': 'current_electricity_36',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A meter bridge contains metallic strips and:',
  'options': ['Gaps forming the bridge arrangement', 'Only batteries', 'Only capacitors', 'No connections'],
  'answer': 0},
 {'id': 'current_electricity_37',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In a meter bridge, a resistance box and unknown resistance are connected in the:',
  'options': ['Bridge gaps', 'Galvanometer coil', 'Metre scale', 'Jockey handle'],
  'answer': 0},
 {'id': 'current_electricity_38',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The galvanometer in a meter bridge is connected between the central point and the:',
  'options': ['Jockey', 'Battery only', 'Rheostat only', 'Resistance box only'],
  'answer': 0},
 {'id': 'current_electricity_39',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The purpose of the jockey is to:',
  'options': ['Slide along the uniform wire to locate the null point',
              'Measure current directly',
              'Supply emf',
              'Change the wire length permanently'],
  'answer': 0},
 {'id': 'current_electricity_40',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A battery and key in a meter bridge are used to:',
  'options': ['Form the circuit', 'Measure resistivity directly', 'Locate the galvanometer', 'Change the scale'],
  'answer': 0},
 {'id': 'current_electricity_41',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A rheostat in a meter bridge is used to:',
  'options': ['Control current', 'Measure length', 'Measure resistance directly', 'Locate the null point automatically'],
  'answer': 0},
 {'id': 'current_electricity_42',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The resistance wire in a meter bridge should have:',
  'options': ['Uniform cross-section', 'Changing cross-section', 'Zero cross-section', 'No resistance'],
  'answer': 0},
 {'id': 'current_electricity_43',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In a meter bridge, the jockey is moved until the galvanometer shows:',
  'options': ['Zero deflection', 'Maximum deflection', 'Infinite deflection', 'A fixed non-zero deflection'],
  'answer': 0},
 {'id': 'current_electricity_44',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The point where the galvanometer shows zero deflection is called the:',
  'options': ['Null point or balance point', 'Critical point', 'End point', 'Resistance point'],
  'answer': 0},
 {'id': 'current_electricity_45',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'If the balance point is at distance l from one end of a 100 cm wire, the other portion has length:',
  'options': ['(100 − l) cm', '(100 + l) cm', 'l/100 cm', '100l cm'],
  'answer': 0},
 {'id': 'current_electricity_46',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'For the usual meter-bridge arrangement, the balance relation given is:',
  'options': ['X/R = l/(100 − l)', 'X/R = 100/l', 'X+R=l', 'X−R=100−l'],
  'answer': 0},
 {'id': 'current_electricity_47',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In the usual meter-bridge relation, X represents the:',
  'options': ['Unknown resistance', 'Known resistance', 'Balancing length', 'Galvanometer resistance'],
  'answer': 0},
 {'id': 'current_electricity_48',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In the usual meter-bridge relation, R represents the:',
  'options': ['Known resistance', 'Unknown resistance', 'Wire length', 'Current'],
  'answer': 0},
 {'id': 'current_electricity_49',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In the usual meter-bridge relation, l represents the:',
  'options': ['Balancing length from the chosen end', 'Resistance of the wire', 'Current through galvanometer', 'Battery emf'],
  'answer': 0},
 {'id': 'current_electricity_50',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The exact resistance-ratio expression in a meter bridge depends on:',
  'options': ['Which resistance is placed in which gap',
              'The colour of the wire',
              'The room temperature only',
              'The name of the galvanometer'],
  'answer': 0},
 {'id': 'current_electricity_51',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'To determine an unknown resistance, the known and unknown resistances are connected in:',
  'options': ['The two gaps', 'The same galvanometer terminal', 'The metre scale', 'The jockey'],
  'answer': 0},
 {'id': 'current_electricity_52',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'After connecting the galvanometer and jockey correctly, the key is:',
  'options': ['Closed', 'Removed permanently', 'Shorted by the jockey', 'Ignored'],
  'answer': 0},
 {'id': 'current_electricity_53',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The resistance/current in a meter bridge is adjusted so that:',
  'options': ['A suitable deflection is obtained',
              'The wire becomes non-uniform',
              'The battery is disconnected',
              'The null point disappears'],
  'answer': 0},
 {'id': 'current_electricity_54',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'To find the balance point, the jockey is touched at:',
  'options': ['Different positions along the wire', 'Only one fixed position', 'The battery terminal', 'The galvanometer coil'],
  'answer': 0},
 {'id': 'current_electricity_55',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'At the balance point, one should measure the:',
  'options': ['Balancing length', 'Mass of the wire', 'Battery mass', 'Galvanometer area'],
  'answer': 0},
 {'id': 'current_electricity_56',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'After finding the balancing length, the next major step is to apply the:',
  'options': ['Wheatstone bridge balance condition', 'Surface tension law', 'Newton’s law', 'Gas law'],
  'answer': 0},
 {'id': 'current_electricity_57',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Interchanging the positions of known and unknown resistances and repeating the experiment helps:',
  'options': ['Reduce experimental error', 'Increase contact resistance', 'Remove the wire', 'Stop the current'],
  'answer': 0},
 {'id': 'current_electricity_58',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Taking the average of repeated meter-bridge measurements helps:',
  'options': ['Reduce experimental error', 'Increase the balancing length', 'Increase emf', 'Make the wire non-uniform'],
  'answer': 0},
 {'id': 'current_electricity_59',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A meter-bridge resistance wire should be uniform in:',
  'options': ['Cross-section', 'Colour', 'Temperature only', 'Length of the jockey'],
  'answer': 0},
 {'id': 'current_electricity_60',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The balancing point should preferably be:',
  'options': ['Near the middle of the wire', 'Very close to an end', 'Outside the wire', 'At the battery terminal'],
  'answer': 0},
 {'id': 'current_electricity_61',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The null point should be avoided very close to:',
  'options': ['Either end of the wire', 'The middle only', 'The galvanometer', 'The key'],
  'answer': 0},
 {'id': 'current_electricity_62',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'The jockey should be:',
  'options': ['Tapped lightly rather than dragged along the wire',
              'Dragged forcefully along the wire',
              'Used as a battery',
              'Pressed continuously at one end'],
  'answer': 0},
 {'id': 'current_electricity_63',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Connections at the end gaps of a meter bridge should be:',
  'options': ['Tight', 'Loose', 'Disconnected', 'Made through water'],
  'answer': 0},
 {'id': 'current_electricity_64',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Contact resistance can affect the:',
  'options': ['Meter-bridge result', 'Length of the metre scale', 'Colour of the wire', 'Battery shape'],
  'answer': 0},
 {'id': 'current_electricity_65',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'End effects can affect measurements in a:',
  'options': ['Meter bridge', 'Only galvanometer', 'Only battery', 'Only rheostat'],
  'answer': 0},
 {'id': 'current_electricity_66',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A meter bridge can be used to determine:',
  'options': ['Specific resistance (resistivity) of a material', 'Only mass', 'Only temperature', 'Only charge'],
  'answer': 0},
 {'id': 'current_electricity_67',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'For a wire, the resistivity formula given in the material is:',
  'options': ['ρ = RA/L', 'ρ = RL/A', 'ρ = AL/R', 'ρ = R/(AL)'],
  'answer': 0},
 {'id': 'current_electricity_68',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In ρ = RA/L, R represents:',
  'options': ['Resistance', 'Resistivity', 'Length', 'Area'],
  'answer': 0},
 {'id': 'current_electricity_69',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In ρ = RA/L, A represents:',
  'options': ['Cross-sectional area', 'Resistance', 'Length', 'Current'],
  'answer': 0},
 {'id': 'current_electricity_70',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'In ρ = RA/L, L represents:',
  'options': ['Length', 'Area', 'Resistance', 'Current'],
  'answer': 0},
 {'id': 'current_electricity_71',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A method to minimise meter-bridge errors is to use:',
  'options': ['A uniform resistance wire', 'A highly irregular wire', 'A broken wire', 'No wire'],
  'answer': 0},
 {'id': 'current_electricity_72',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Another method to minimise errors is to adjust the known resistance so that the null point is:',
  'options': ['Near the middle of the wire', 'Near an end', 'Outside the wire', 'At the battery'],
  'answer': 0},
 {'id': 'current_electricity_73',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Which quantity is zero at Wheatstone bridge balance according to the material?',
  'options': ['Galvanometer current', 'Resistance of every arm', 'Battery emf', 'All branch currents'],
  'answer': 0},
 {'id': 'current_electricity_74',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Which condition indicates that the two galvanometer junctions are equipotential?',
  'options': ['No current flows through the galvanometer',
              'Current is maximum through galvanometer',
              'Resistance is infinite in every arm',
              'The battery is removed'],
  'answer': 0},
 {'id': 'current_electricity_75',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Which law is applied at suitable junctions in a multi-branch circuit?',
  'options': ['Kirchhoff’s first law', 'Kirchhoff’s second law only', 'Wheatstone balance condition', 'Meter-bridge formula'],
  'answer': 0},
 {'id': 'current_electricity_76',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Which law is applied around suitable independent loops?',
  'options': ['Kirchhoff’s second law', 'Kirchhoff’s first law only', 'Meter-bridge law', 'Surface tension law'],
  'answer': 0},
 {'id': 'current_electricity_77',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'A negative calculated current in Kirchhoff’s method indicates an error in the:',
  'options': ['Initially assumed direction, not necessarily the equations',
              'Existence of the circuit',
              'Battery voltage only',
              'Resistance value only'],
  'answer': 0},
 {'id': 'current_electricity_78',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Which device is specifically used to locate the null point in a meter bridge?',
  'options': ['Jockey and galvanometer', 'Rheostat alone', 'Battery alone', 'Resistance box alone'],
  'answer': 0},
 {'id': 'current_electricity_79',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Which component is used to control current in a meter bridge?',
  'options': ['Rheostat', 'Jockey', 'Galvanometer', 'Metre scale'],
  'answer': 0},
 {'id': 'current_electricity_80',
  'subject': 'Physics',
  'topic': 'Current Electricity',
  'q': 'Which component detects the zero-deflection condition in a meter bridge?',
  'options': ['Galvanometer', 'Rheostat', 'Battery', 'Resistance box'],
  'answer': 0},
 {'id': 'halogen_001',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'What are halogen derivatives of hydrocarbons?',
  'options': ['Compounds formed by replacing one or more H atoms of hydrocarbons by halogen atoms',
              'Compounds formed by replacing halogen atoms by H',
              'Compounds containing only oxygen',
              'Compounds containing only nitrogen'],
  'answer': 0},
 {'id': 'halogen_002',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Haloalkanes are also called:',
  'options': ['Alkyl halides', 'Aryl ethers', 'Alcohols', 'Aldehydes'],
  'answer': 0},
 {'id': 'halogen_003',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In an alkyl halide, the halogen is bonded to carbon that is generally:',
  'options': ['sp3 hybridised', 'sp2 hybridised', 'sp hybridised', 'sp3d hybridised'],
  'answer': 0},
 {'id': 'halogen_004',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In a primary alkyl halide, the carbon bearing halogen is attached to:',
  'options': ['One other carbon', 'Two other carbons', 'Three other carbons', 'No carbon'],
  'answer': 0},
 {'id': 'halogen_005',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In a secondary alkyl halide, the carbon bearing halogen is attached to:',
  'options': ['Two other carbons', 'One other carbon', 'Three other carbons', 'Four other carbons'],
  'answer': 0},
 {'id': 'halogen_006',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In a tertiary alkyl halide, the carbon bearing halogen is attached to:',
  'options': ['Three other carbons', 'One other carbon', 'Two other carbons', 'No carbon'],
  'answer': 0},
 {'id': 'halogen_007',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A benzylic halide has halogen attached to a carbon:',
  'options': ['Adjacent to an aromatic ring', 'Directly on an aromatic ring', 'Of a carbonyl group', 'Of an alkyne'],
  'answer': 0},
 {'id': 'halogen_008',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'An allylic halide has halogen attached to a carbon:',
  'options': ['Adjacent to a C=C bond', 'Directly on a C=C carbon', 'Adjacent to a C≡C bond only', 'Of a carbonyl group'],
  'answer': 0},
 {'id': 'halogen_009',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A vinylic halide has halogen directly attached to:',
  'options': ['An sp2 carbon of a C=C bond', 'An sp3 carbon next to C=C', 'An aromatic side-chain carbon', 'An oxygen atom'],
  'answer': 0},
 {'id': 'halogen_010',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'An aryl halide has halogen directly bonded to:',
  'options': ['An aromatic-ring carbon', 'An alkyl carbon', 'An oxygen atom', 'A carbonyl carbon'],
  'answer': 0},
 {'id': 'halogen_011',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The IUPAC name of CH3Cl is:',
  'options': ['Chloromethane', 'Chloroethane', 'Dichloromethane', 'Methyl bromide'],
  'answer': 0},
 {'id': 'halogen_012',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The IUPAC name of CH3CH2Br is:',
  'options': ['Bromoethane', 'Bromomethane', '1-Bromopropane', 'Ethyl chloride'],
  'answer': 0},
 {'id': 'halogen_013',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The IUPAC name of CH3CH(Cl)CH3 is:',
  'options': ['2-Chloropropane', '1-Chloropropane', 'Chloroethane', '2-Chlorobutane'],
  'answer': 0},
 {'id': 'halogen_014',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'CH3CH2CH2I is named:',
  'options': ['1-Iodopropane', '2-Iodopropane', 'Iodoethane', 'Propyl chloride'],
  'answer': 0},
 {'id': 'halogen_015',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The functional group in haloalkanes is represented as:',
  'options': ['R–X', 'R–OH', 'R–CHO', 'R–COOH'],
  'answer': 0},
 {'id': 'halogen_016',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In the formula R–X, X commonly represents:',
  'options': ['F, Cl, Br or I', 'Only O', 'Only N', 'Only S'],
  'answer': 0},
 {'id': 'halogen_017',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The carbon–halogen bond is generally:',
  'options': ['Polar covalent', 'Purely ionic', 'Nonpolar metallic', 'Hydrogen bonded'],
  'answer': 0},
 {'id': 'halogen_018',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Among common halogens, the C–F bond is generally:',
  'options': ['Strongest', 'Weakest', 'Always ionic', 'Absent in haloalkanes'],
  'answer': 0},
 {'id': 'halogen_019',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'As the size of halogen increases from F to I, the C–X bond generally becomes:',
  'options': ['Longer', 'Shorter', 'Unchanged', 'Metallic'],
  'answer': 0},
 {'id': 'halogen_020',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which has the best leaving-group ability among halide ions in ordinary SN reactions?',
  'options': ['I−', 'F−', 'Cl−', 'OH−'],
  'answer': 0},
 {'id': 'halogen_021',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Alcohols can be converted into alkyl chlorides using:',
  'options': ['HCl/ZnCl2', 'NaI/acetone', 'AgF only', 'NaOH only'],
  'answer': 0},
 {'id': 'halogen_022',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Concentrated HCl with anhydrous ZnCl2 is known as:',
  'options': ['Lucas reagent', 'Grignard reagent', 'Swarts reagent', 'Finkelstein reagent'],
  'answer': 0},
 {'id': 'halogen_023',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Alcohols can be converted to alkyl bromides using reagents such as:',
  'options': ['PBr3', 'NaCl only', 'AgF only', 'NaOH'],
  'answer': 0},
 {'id': 'halogen_024',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Alcohols can be converted to alkyl iodides using:',
  'options': ['PI3 or iodide-based reagents', 'AgF only', 'HCl only', 'NaOH only'],
  'answer': 0},
 {'id': 'halogen_025',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Finkelstein reaction is used mainly to prepare:',
  'options': ['Alkyl iodides', 'Alkyl fluorides', 'Alcohols', 'Aryl amines'],
  'answer': 0},
 {'id': 'halogen_026',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Finkelstein reaction commonly uses NaI in:',
  'options': ['Dry acetone', 'Water', 'Concentrated H2SO4', 'Ethanol only'],
  'answer': 0},
 {'id': 'halogen_027',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In Finkelstein reaction, the precipitate formed helps drive the reaction because:',
  'options': ['NaCl or NaBr is poorly soluble in acetone', 'NaI is insoluble in acetone', 'Alcohol is formed', 'The substrate evaporates'],
  'answer': 0},
 {'id': 'halogen_028',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Swarts reaction is commonly used to prepare:',
  'options': ['Alkyl fluorides', 'Alkyl iodides', 'Alcohols', 'Amines'],
  'answer': 0},
 {'id': 'halogen_029',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Swarts reaction may use:',
  'options': ['Metal fluorides such as AgF', 'NaI in acetone', 'Aqueous KOH', 'HCl/ZnCl2'],
  'answer': 0},
 {'id': 'halogen_030',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Alkyl halides react with aqueous KOH mainly to form:',
  'options': ['Alcohols', 'Alkenes', 'Ethers', 'Alkynes'],
  'answer': 0},
 {'id': 'halogen_031',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Alkyl halides with alcoholic KOH generally undergo:',
  'options': ['Dehydrohalogenation', 'Hydration', 'Oxidation to aldehydes', 'Esterification'],
  'answer': 0},
 {'id': 'halogen_032',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Dehydrohalogenation of an alkyl halide removes:',
  'options': ['HX', 'H2O', 'O2', 'CO2'],
  'answer': 0},
 {'id': 'halogen_033',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In beta elimination, the hydrogen removed is usually from the:',
  'options': ['β-carbon', 'α-carbon bearing halogen', 'Halogen atom', 'Oxygen atom'],
  'answer': 0},
 {'id': 'halogen_034',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'According to Saytzeff rule, the major alkene is generally the:',
  'options': ['More substituted alkene', 'Less substituted alkene', 'Alkane', 'Alcohol'],
  'answer': 0},
 {'id': 'halogen_035',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A nucleophile is a species that:',
  'options': ['Donates an electron pair', 'Accepts an electron pair only', 'Donates a proton only', 'Always loses an electron'],
  'answer': 0},
 {'id': 'halogen_036',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In nucleophilic substitution of R–X, X usually acts as:',
  'options': ['Leaving group', 'Nucleophile', 'Catalyst', 'Solvent'],
  'answer': 0},
 {'id': 'halogen_037',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'SN2 reaction is:',
  'options': ['One-step bimolecular substitution',
              'Two-step unimolecular substitution',
              'A radical chain reaction',
              'Electrophilic addition'],
  'answer': 0},
 {'id': 'halogen_038',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The rate law for an SN2 reaction depends on:',
  'options': ['Both substrate and nucleophile concentrations',
              'Substrate concentration only',
              'Nucleophile concentration only',
              'Solvent concentration only'],
  'answer': 0},
 {'id': 'halogen_039',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'SN2 nucleophilic attack occurs mainly from the:',
  'options': ['Back side of the C–X bond', 'Front side of the C–X bond', 'Side of the halogen only', 'Top of the molecule'],
  'answer': 0},
 {'id': 'halogen_040',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Backside attack in SN2 commonly causes:',
  'options': ['Inversion of configuration', 'Racemisation in every case', 'No stereochemical change', 'Only elimination'],
  'answer': 0},
 {'id': 'halogen_041',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'SN1 reaction proceeds through formation of a:',
  'options': ['Carbocation intermediate', 'Carbanion intermediate', 'Free metal intermediate', 'Hydrogen-bonded intermediate'],
  'answer': 0},
 {'id': 'halogen_042',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The rate of an SN1 reaction mainly depends on:',
  'options': ['Concentration of substrate',
              'Concentration of nucleophile',
              'Concentration of leaving-group ion only',
              'Concentration of water only'],
  'answer': 0},
 {'id': 'halogen_043',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which substrate generally favours SN1?',
  'options': ['Tertiary alkyl halide', 'Methyl halide', 'Primary alkyl halide', 'Vinylic halide'],
  'answer': 0},
 {'id': 'halogen_044',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which substrate generally favours SN2?',
  'options': ['Methyl or primary alkyl halide', 'Tertiary alkyl halide', 'Aryl halide', 'Highly hindered tertiary halide'],
  'answer': 0},
 {'id': 'halogen_045',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Secondary alkyl halides can undergo:',
  'options': ['SN1 or SN2 depending on conditions', 'Only SN1', 'Only SN2', 'Neither substitution nor elimination'],
  'answer': 0},
 {'id': 'halogen_046',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Tertiary alkyl halides are strongly hindered toward:',
  'options': ['SN2 attack', 'SN1 ionisation', 'Carbocation formation', 'Solvolysis'],
  'answer': 0},
 {'id': 'halogen_047',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A polar protic solvent generally favours:',
  'options': ['SN1 ionisation', 'SN2 equally in all cases', 'No ionic reaction', 'Only radical substitution'],
  'answer': 0},
 {'id': 'halogen_048',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A polar aprotic solvent can favour:',
  'options': ['SN2 reactions', 'Only SN1 reactions', 'Only radical reactions', 'Only electrophilic substitution'],
  'answer': 0},
 {'id': 'halogen_049',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The intermediate in SN1 is:',
  'options': ['Carbocation', 'Carbanion', 'Nitrene', 'Carbene'],
  'answer': 0},
 {'id': 'halogen_050',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Carbocation stability generally follows:',
  'options': ['3° > 2° > 1° > methyl', '1° > 2° > 3° > methyl', 'methyl > 1° > 2° > 3°', '2° > 3° > 1° > methyl'],
  'answer': 0},
 {'id': 'halogen_051',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'SN2 reaction is favoured by a:',
  'options': ['Strong nucleophile', 'Very weak nucleophile in every case', 'Highly crowded substrate', 'Stable carbocation'],
  'answer': 0},
 {'id': 'halogen_052',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Elimination and substitution are competing reactions of:',
  'options': ['Haloalkanes', 'Only alcohols', 'Only alkenes', 'Only carboxylic acids'],
  'answer': 0},
 {'id': 'halogen_053',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Aryl halides are generally less reactive toward ordinary SN2 because:',
  'options': ['The C–X bond has partial double-bond character and the carbon is sp2',
              'They contain no halogen',
              'They are always ionic',
              'The ring contains oxygen'],
  'answer': 0},
 {'id': 'halogen_054',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The C–Cl bond in chlorobenzene is shorter than in chloroethane mainly because:',
  'options': ['Resonance gives partial double-bond character',
              'Chlorobenzene is ionic',
              'Chloroethane is aromatic',
              'Chlorine is absent in chloroethane'],
  'answer': 0},
 {'id': 'halogen_055',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Chlorobenzene generally does not undergo easy SN1 because formation of the required:',
  'options': ['Phenyl cation is highly unstable', 'Methyl cation is unstable', 'Alcohol is impossible', 'Fluoride ion is unstable'],
  'answer': 0},
 {'id': 'halogen_056',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Wurtz reaction couples alkyl halides using:',
  'options': ['Sodium in dry ether', 'NaI in acetone', 'AgF in heat', 'Aqueous KOH'],
  'answer': 0},
 {'id': 'halogen_057',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The major product of Wurtz reaction from CH3Br is:',
  'options': ['Ethane', 'Methane', 'Ethene', 'Methanol'],
  'answer': 0},
 {'id': 'halogen_058',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Wurtz reaction is particularly useful for preparing:',
  'options': ['Higher alkanes with symmetrical carbon skeletons', 'Aryl alcohols', 'Alkenes only', 'Amines'],
  'answer': 0},
 {'id': 'halogen_059',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Wurtz-Fittig reaction involves coupling of:',
  'options': ['An alkyl halide and an aryl halide', 'Two alcohols', 'Two acids', 'An alkene and an alcohol'],
  'answer': 0},
 {'id': 'halogen_060',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Fittig reaction couples:',
  'options': ['Aryl halides', 'Alcohols', 'Alkenes', 'Amines'],
  'answer': 0},
 {'id': 'halogen_061',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A Grignard reagent has the general formula:',
  'options': ['R–Mg–X', 'R–Na–OH', 'R–OH', 'R–X–MgOH'],
  'answer': 0},
 {'id': 'halogen_062',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Grignard reagents are commonly prepared by reacting alkyl/aryl halides with Mg in:',
  'options': ['Dry ether', 'Water', 'Concentrated nitric acid', 'Aqueous KOH'],
  'answer': 0},
 {'id': 'halogen_063',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Moisture must be excluded during Grignard reagent preparation because Grignard reagents:',
  'options': ['React readily with water', 'Are insoluble in ether only', 'Need water as catalyst', 'Are oxidised by nitrogen'],
  'answer': 0},
 {'id': 'halogen_064',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'RMgX behaves as a strong:',
  'options': ['Nucleophile/base', 'Electrophile only', 'Oxidising agent only', 'Leaving group only'],
  'answer': 0},
 {'id': 'halogen_065',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'On reaction with water, RMgX gives:',
  'options': ['RH', 'ROH', 'R–X again only', 'R–COOH directly'],
  'answer': 0},
 {'id': 'halogen_066',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'On carbonation followed by hydrolysis, a Grignard reagent generally gives:',
  'options': ['A carboxylic acid with one extra carbon', 'An alkene with one less carbon', 'An amine', 'An ether'],
  'answer': 0},
 {'id': 'halogen_067',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'RMgX reacts with formaldehyde followed by hydrolysis to give a:',
  'options': ['Primary alcohol', 'Secondary alcohol', 'Tertiary alcohol', 'Ketone only'],
  'answer': 0},
 {'id': 'halogen_068',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'RMgX reacts with an aldehyde other than formaldehyde followed by hydrolysis to give a:',
  'options': ['Secondary alcohol', 'Primary alcohol', 'Tertiary alcohol', 'Carboxylic acid only'],
  'answer': 0},
 {'id': 'halogen_069',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'RMgX reacts with a ketone followed by hydrolysis to give a:',
  'options': ['Tertiary alcohol', 'Primary alcohol', 'Secondary alcohol', 'Haloalkane'],
  'answer': 0},
 {'id': 'halogen_070',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The Grignard reagent attacks the carbonyl carbon because that carbon is:',
  'options': ['Electrophilic', 'Nucleophilic', 'Aromatic only', 'Metallic'],
  'answer': 0},
 {'id': 'halogen_071',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In an SN2 reaction, increasing steric hindrance around the reacting carbon generally:',
  'options': ['Decreases the reaction rate', 'Increases the reaction rate', 'Has no effect', 'Makes the substrate aromatic'],
  'answer': 0},
 {'id': 'halogen_072',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The order of SN2 reactivity for simple alkyl halides is generally:',
  'options': ['Methyl > primary > secondary >> tertiary',
              'Tertiary > secondary > primary > methyl',
              'Secondary > tertiary > methyl > primary',
              'Primary > tertiary > methyl > secondary'],
  'answer': 0},
 {'id': 'halogen_073',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The order of SN1 reactivity for simple alkyl halides generally follows:',
  'options': ['Tertiary > secondary > primary > methyl',
              'Methyl > primary > secondary > tertiary',
              'Primary > secondary > tertiary > methyl',
              'Secondary > methyl > tertiary > primary'],
  'answer': 0},
 {'id': 'halogen_074',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A good leaving group is generally the conjugate base of a:',
  'options': ['Strong acid', 'Strong base', 'Strong nucleophile only', 'Weak acid only'],
  'answer': 0},
 {'id': 'halogen_075',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Among F−, Cl−, Br− and I−, the best leaving group is generally:',
  'options': ['I−', 'F−', 'Cl−', 'OH−'],
  'answer': 0},
 {'id': 'halogen_076',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In aqueous KOH substitution, the attacking species is mainly:',
  'options': ['OH−', 'H2O only', 'K+', 'X+'],
  'answer': 0},
 {'id': 'halogen_077',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In alcoholic KOH elimination, the base abstracts:',
  'options': ['A β-hydrogen', 'The halogen nucleus', 'A carbonyl oxygen', 'A metal ion'],
  'answer': 0},
 {'id': 'halogen_078',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A haloalkane containing two halogen atoms is called a:',
  'options': ['Dihaloalkane', 'Monohaloalkane', 'Triol', 'Diene'],
  'answer': 0},
 {'id': 'halogen_079',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A compound containing three halogen atoms is called a:',
  'options': ['Trihalo compound', 'Monohalo compound', 'Dialcohol', 'Triene'],
  'answer': 0},
 {'id': 'halogen_080',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Gem-dihalide has two halogen atoms attached to:',
  'options': ['The same carbon atom', 'Adjacent different carbons', 'An oxygen atom', 'Two nitrogen atoms'],
  'answer': 0},
 {'id': 'halogen_081',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Vicinal dihalide has two halogen atoms attached to:',
  'options': ['Adjacent carbon atoms', 'The same carbon atom', 'Only aromatic carbon', 'Oxygen atoms'],
  'answer': 0},
 {'id': 'halogen_082',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Ethylene dibromide is a:',
  'options': ['Vicinal dihalide', 'Gem-dihalide', 'Monohalide', 'Aryl halide'],
  'answer': 0},
 {'id': 'halogen_083',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Methylene chloride is commonly known as:',
  'options': ['Dichloromethane', 'Chloroform', 'Carbon tetrachloride', 'Methyl chloride'],
  'answer': 0},
 {'id': 'halogen_084',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Chloroform has the formula:',
  'options': ['CHCl3', 'CH2Cl2', 'CCl4', 'CH3Cl'],
  'answer': 0},
 {'id': 'halogen_085',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Carbon tetrachloride has the formula:',
  'options': ['CCl4', 'CHCl3', 'CH2Cl2', 'CH3Cl'],
  'answer': 0},
 {'id': 'halogen_086',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Iodoform has the formula:',
  'options': ['CHI3', 'CHCl3', 'CCl4', 'CH3I'],
  'answer': 0},
 {'id': 'halogen_087',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which haloalkane is generally more polarizable due to the larger halogen atom?',
  'options': ['Iodoalkane', 'Fluoroalkane', 'Chloroalkane only', 'None'],
  'answer': 0},
 {'id': 'halogen_088',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Boiling points of homologous haloalkanes generally increase with:',
  'options': ['Increasing molecular mass/chain length',
              'Decreasing chain length only',
              'Removing the halogen',
              'Decreasing polarizability'],
  'answer': 0},
 {'id': 'halogen_089',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Haloalkanes are generally:',
  'options': ['Poorly soluble in water but soluble in many organic solvents',
              'Highly soluble in water',
              'Always ionic in water',
              'Insoluble in all organic solvents'],
  'answer': 0},
 {'id': 'halogen_090',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The density of many bromo- and iodoalkanes is relatively high mainly because of:',
  'options': ['Heavy halogen atoms', 'Hydrogen bonding only', 'Low molecular mass', 'Presence of oxygen'],
  'answer': 0},
 {'id': 'halogen_091',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The carbon-halogen bond polarity arises mainly because halogens are:',
  'options': ['More electronegative than carbon', 'Less electronegative than carbon in all cases', 'Metallic', 'Inert gases'],
  'answer': 0},
 {'id': 'halogen_092',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In a nucleophilic substitution reaction, the nucleophile attacks the:',
  'options': ['Electrophilic carbon attached to the leaving group', 'Halogen nucleus only', 'Solvent molecule only', 'Counterion only'],
  'answer': 0},
 {'id': 'halogen_093',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A reaction in which one atom/group replaces another is called:',
  'options': ['Substitution reaction', 'Addition reaction', 'Elimination only', 'Polymerisation only'],
  'answer': 0},
 {'id': 'halogen_094',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Removal of two groups from adjacent carbons to form a double bond is:',
  'options': ['Elimination', 'Substitution', 'Hydrolysis', 'Neutralisation'],
  'answer': 0},
 {'id': 'halogen_095',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A haloalkane can be converted to an alkene by heating with:',
  'options': ['Alcoholic KOH', 'Aqueous KOH only', 'AgF only', 'NaI/acetone'],
  'answer': 0},
 {'id': 'halogen_096',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A haloalkane can be converted to an alcohol by heating with:',
  'options': ['Aqueous KOH', 'Alcoholic KOH only', 'NaI/acetone', 'Mg/dry ether'],
  'answer': 0},
 {'id': 'halogen_097',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The product of CH3CH2Br with aqueous KOH is mainly:',
  'options': ['Ethanol', 'Ethene', 'Ethane', 'Ethoxyethane'],
  'answer': 0},
 {'id': 'halogen_098',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The product of CH3CH2Br with alcoholic KOH is mainly:',
  'options': ['Ethene', 'Ethanol', 'Ethane', 'Bromoethane'],
  'answer': 0},
 {'id': 'halogen_099',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The reagent combination Mg/dry ether converts an alkyl halide into:',
  'options': ['A Grignard reagent', 'An alcohol directly', 'An alkene directly', 'A carboxylic acid directly'],
  'answer': 0},
 {'id': 'halogen_100',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The carbon bonded to Mg in RMgX has a character that is:',
  'options': ['Nucleophilic/carbanion-like', 'Strongly electrophilic', 'Neutral like an alkane', 'Aromatic'],
  'answer': 0},
 {'id': 'halogen_101',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Grignard reagents are destroyed by:',
  'options': ['Water', 'Dry ether', 'Nitrogen gas', 'Dry hydrocarbons'],
  'answer': 0},
 {'id': 'halogen_102',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The solvent used for Grignard reagent preparation should be:',
  'options': ['Anhydrous ether', 'Water', 'Aqueous alcohol', 'Dilute HCl'],
  'answer': 0},
 {'id': 'halogen_103',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Aryl halides can be prepared from aromatic diazonium salts by:',
  'options': ['Sandmeyer-type reactions', 'Finkelstein reaction only', 'Wurtz reaction only', 'Hydration'],
  'answer': 0},
 {'id': 'halogen_104',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In the Sandmeyer reaction, a diazonium group can be replaced by:',
  'options': ['Cl, Br or CN depending on the reagent', 'Only OH', 'Only Mg', 'Only H2O'],
  'answer': 0},
 {'id': 'halogen_105',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The reagent commonly used with CuCl in Sandmeyer reaction introduces:',
  'options': ['Cl', 'Br', 'I', 'OH'],
  'answer': 0},
 {'id': 'halogen_106',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The reagent commonly used with CuBr in Sandmeyer reaction introduces:',
  'options': ['Br', 'Cl', 'I', 'OH'],
  'answer': 0},
 {'id': 'halogen_107',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Aryl iodides can be prepared from diazonium salts using:',
  'options': ['KI', 'NaOH only', 'Mg only', 'AgF only'],
  'answer': 0},
 {'id': 'halogen_108',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Aryl fluorides can be prepared by the:',
  'options': ['Balz–Schiemann reaction', 'Wurtz reaction', 'Finkelstein reaction', 'Lucas reaction'],
  'answer': 0},
 {'id': 'halogen_109',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Balz–Schiemann reaction is associated with preparation of:',
  'options': ['Aryl fluorides', 'Alkyl iodides', 'Alcohols', 'Alkenes'],
  'answer': 0},
 {'id': 'halogen_110',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'In Balz–Schiemann reaction, the diazonium tetrafluoroborate is:',
  'options': ['Heated to form aryl fluoride',
              'Treated with NaI to form alkyl iodide',
              'Hydrolysed to alcohol only',
              'Reduced to alkane only'],
  'answer': 0},
 {'id': 'halogen_111',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which type of halide generally undergoes SN2 readily?',
  'options': ['Methyl halide', 'Tertiary aryl halide', 'Vinylic halide', 'Highly hindered tertiary halide'],
  'answer': 0},
 {'id': 'halogen_112',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which type of carbon cannot easily undergo normal SN2 displacement at the C–X bond?',
  'options': ['Vinylic carbon', 'Primary sp3 carbon', 'Methyl carbon', 'Secondary sp3 carbon'],
  'answer': 0},
 {'id': 'halogen_113',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'A carbocation rearrangement is most relevant to:',
  'options': ['SN1-type reactions', 'SN2 reactions', 'Finkelstein precipitation', 'Swarts reaction'],
  'answer': 0},
 {'id': 'halogen_114',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'SN1 reactions can lead to:',
  'options': ['Racemisation when a chiral carbocation is formed',
              'Only inversion in every case',
              'Only retention in every case',
              'No stereochemical change ever'],
  'answer': 0},
 {'id': 'halogen_115',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The molecularity of an elementary SN2 reaction is:',
  'options': ['Two', 'One', 'Three', 'Zero'],
  'answer': 0},
 {'id': 'halogen_116',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The molecularity of the rate-determining SN1 ionisation step is:',
  'options': ['One', 'Two', 'Three', 'Four'],
  'answer': 0},
 {'id': 'halogen_117',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which reaction is driven by precipitation of an inorganic halide in acetone?',
  'options': ['Finkelstein reaction', 'Wurtz reaction', 'Lucas test', 'Grignard formation'],
  'answer': 0},
 {'id': 'halogen_118',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'Which reagent is a strong fluorinating agent in the Swarts method?',
  'options': ['AgF', 'NaI', 'NaCl', 'KOH'],
  'answer': 0},
 {'id': 'halogen_119',
  'subject': 'Chemistry',
  'topic': 'Halogen Derivatives',
  'q': 'The major purpose of dry ether in Grignard chemistry is to:',
  'options': ['Provide a moisture-free coordinating medium', 'Supply hydroxide ions', 'Act as a strong acid', 'Oxidise the reagent'],
  'answer': 0},
 {'id': 'rot_01',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Uniform circular motion is motion along a circle with:',
  'options': ['Constant speed', 'Constant direction', 'Zero velocity', 'Zero radius'],
  'answer': 0},
 {'id': 'rot_02',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In circular motion, the direction of velocity continuously:',
  'options': ['Changes', 'Remains fixed', 'Becomes zero', 'Becomes radial only'],
  'answer': 0},
 {'id': 'rot_03',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Uniform circular motion is a type of:',
  'options': ['Accelerated motion', 'Unaccelerated motion', 'Linear rest', 'Pure translation only'],
  'answer': 0},
 {'id': 'rot_04',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The acceleration that changes the direction of velocity in circular motion is:',
  'options': ['Centripetal (radial) acceleration', 'Tangential acceleration only', 'Gravitational acceleration only', 'Zero acceleration'],
  'answer': 0},
 {'id': 'rot_05',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Centripetal acceleration is directed:',
  'options': ['Towards the centre', 'Away from the centre', 'Along the tangent', 'Vertically upward always'],
  'answer': 0},
 {'id': 'rot_06',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For uniform circular motion, the magnitude of velocity is:',
  'options': ['Constant', 'Continuously increasing', 'Continuously decreasing', 'Zero'],
  'answer': 0},
 {'id': 'rot_07',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Non-uniform circular motion involves change in:',
  'options': ['Speed as well as direction of velocity', 'Direction only', 'Mass only', 'Radius only'],
  'answer': 0},
 {'id': 'rot_08',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Tangential acceleration is associated with change in:',
  'options': ['Magnitude of velocity', 'Direction only', 'Mass', 'Radius only'],
  'answer': 0},
 {'id': 'rot_09',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Total acceleration in non-uniform circular motion is the resultant of:',
  'options': ['Radial and tangential accelerations', 'Only radial forces', 'Only tangential velocity', 'Weight and mass'],
  'answer': 0},
 {'id': 'rot_10',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'A radius vector is drawn from the centre of the circle to the:',
  'options': ['Position of the object', 'Tangential direction', 'Centre of mass only', 'Point of contact only'],
  'answer': 0},
 {'id': 'rot_11',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular displacement is the angle traced by the:',
  'options': ['Radius vector at the centre', 'Tangent at the surface', 'Velocity vector only', 'Acceleration vector only'],
  'answer': 0},
 {'id': 'rot_12',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular displacement is a:',
  'options': ['Vector quantity', 'Scalar quantity', 'Dimensionless mass', 'Force'],
  'answer': 0},
 {'id': 'rot_13',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The SI unit of angular displacement is:',
  'options': ['Radian', 'Metre', 'Second', 'Newton'],
  'answer': 0},
 {'id': 'rot_14',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'One complete revolution corresponds to:',
  'options': ['2π radians', 'π/2 radians', 'π radians', '1 radian'],
  'answer': 0},
 {'id': 'rot_15',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular velocity is the rate of change of:',
  'options': ['Angular displacement', 'Linear displacement', 'Mass', 'Force'],
  'answer': 0},
 {'id': 'rot_16',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular velocity is represented by:',
  'options': ['ω', 'α', 'τ', 'I'],
  'answer': 0},
 {'id': 'rot_17',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The direction of an angular velocity vector is given using the:',
  'options': ['Right-hand thumb rule', 'Left-hand rule only', 'Parallel-axis theorem', 'Law of inertia'],
  'answer': 0},
 {'id': 'rot_18',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For uniform circular motion, angular velocity is:',
  'options': ['Constant', 'Zero', 'Always increasing', 'Always decreasing'],
  'answer': 0},
 {'id': 'rot_19',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular velocity for a motion of period T is:',
  'options': ['2π/T', 'T/2π', '2πT', 'T²/2π'],
  'answer': 0},
 {'id': 'rot_20',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Frequency f and period T are related by:',
  'options': ['f = 1/T', 'f = T', 'f = 2πT', 'f = T²'],
  'answer': 0},
 {'id': 'rot_21',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular acceleration is the rate of change of:',
  'options': ['Angular velocity', 'Angular displacement only', 'Radius', 'Mass'],
  'answer': 0},
 {'id': 'rot_22',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular acceleration is represented by:',
  'options': ['α', 'ω', 'τ', 'L'],
  'answer': 0},
 {'id': 'rot_23',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For uniform circular motion, angular acceleration is:',
  'options': ['Zero', 'Maximum', 'Negative infinity', 'Equal to radius'],
  'answer': 0},
 {'id': 'rot_24',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Tangential velocity and angular velocity are related by:',
  'options': ['v = rω', 'v = ω/r', 'v = r/ω', 'v = rω²'],
  'answer': 0},
 {'id': 'rot_25',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Centripetal acceleration can be written as:',
  'options': ['v²/r', 'vr', 'r/v²', 'v/r²'],
  'answer': 0},
 {'id': 'rot_26',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Using angular velocity, centripetal acceleration is:',
  'options': ['rω²', 'r/ω²', 'ω/r', 'r²ω'],
  'answer': 0},
 {'id': 'rot_27',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Tangential acceleration is related to angular acceleration by:',
  'options': ['a_t = rα', 'a_t = α/r', 'a_t = r/α', 'a_t = rα²'],
  'answer': 0},
 {'id': 'rot_28',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For circular motion, radial acceleration is also called:',
  'options': ['Centripetal acceleration', 'Tangential acceleration', 'Angular acceleration', 'Linear acceleration only'],
  'answer': 0},
 {'id': 'rot_29',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The translational quantity analogous to angular displacement is:',
  'options': ['Linear displacement', 'Linear momentum', 'Force', 'Mass'],
  'answer': 0},
 {'id': 'rot_30',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The rotational quantity analogous to linear velocity is:',
  'options': ['Angular velocity', 'Torque', 'Angular momentum', 'Moment of inertia'],
  'answer': 0},
 {'id': 'rot_31',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The rotational quantity analogous to linear acceleration is:',
  'options': ['Angular acceleration', 'Angular displacement', 'Torque', 'Work'],
  'answer': 0},
 {'id': 'rot_32',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The rotational quantity analogous to mass is:',
  'options': ['Moment of inertia', 'Torque', 'Angular velocity', 'Angular displacement'],
  'answer': 0},
 {'id': 'rot_33',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The rotational quantity analogous to linear momentum is:',
  'options': ['Angular momentum', 'Torque', 'Power', 'Angular acceleration'],
  'answer': 0},
 {'id': 'rot_34',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Torque is the rotational analogue of:',
  'options': ['Force', 'Mass', 'Velocity', 'Displacement'],
  'answer': 0},
 {'id': 'rot_35',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Rotational work is related to torque and angular displacement by:',
  'options': ['W = τθ', 'W = τ/θ', 'W = θ/τ', 'W = τ²θ'],
  'answer': 0},
 {'id': 'rot_36',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Rotational power is related to torque and angular velocity by:',
  'options': ['P = τω', 'P = τ/ω', 'P = ω/τ', 'P = τω²'],
  'answer': 0},
 {'id': 'rot_37',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The centripetal force required for circular motion is directed:',
  'options': ['Towards the centre', 'Away from the centre', 'Along the tangent', 'Opposite to velocity always'],
  'answer': 0},
 {'id': 'rot_38',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Centrifugal force in the notes is described as:',
  'options': ['An apparent force in a rotating/non-inertial frame',
              'A real force always directed inward',
              'A gravitational force',
              'A magnetic force'],
  'answer': 0},
 {'id': 'rot_39',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Centrifugal force is directed:',
  'options': ['Away from the centre', 'Towards the centre', 'Along the tangent', 'Upward only'],
  'answer': 0},
 {'id': 'rot_40',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'A passenger in a car taking a turn tends to feel an apparent force:',
  'options': ['Outward from the centre of the turn', 'Toward the centre only', 'Vertically downward only', 'Along the road tangent only'],
  'answer': 0},
 {'id': 'rot_41',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'A satellite moving around a planet requires centripetal force supplied by:',
  'options': ['Gravity', 'Surface tension', 'Friction from the road', 'Normal reaction from a road'],
  'answer': 0},
 {'id': 'rot_42',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a vehicle taking a turn on an unbanked road, centripetal force is provided by:',
  'options': ['Friction', 'Gravity alone', 'Normal reaction alone', 'Engine torque alone'],
  'answer': 0},
 {'id': 'rot_43',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The safety speed on a horizontal unbanked curved road depends on:',
  'options': ['Coefficient of friction and radius of curvature', 'Vehicle mass only', 'Colour of vehicle', 'Engine size only'],
  'answer': 0},
 {'id': 'rot_44',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'On an unbanked road, increasing the radius of curvature generally:',
  'options': ['Increases the allowable safe speed', 'Makes safe speed zero', 'Has no effect at all', 'Reverses the direction of friction'],
  'answer': 0},
 {'id': 'rot_45',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The safety speed limit on an unbanked curved road is independent of:',
  'options': ['Mass of the vehicle', 'Coefficient of friction', 'Radius of curvature', 'Road surface condition'],
  'answer': 0},
 {'id': 'rot_46',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Banking of a road means the road surface is:',
  'options': ['Inclined to the horizontal', 'Made perfectly vertical', 'Made perfectly flat', 'Covered with water'],
  'answer': 0},
 {'id': 'rot_47',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In a banked road, the outer edge is raised above the:',
  'options': ['Inner edge', 'Centre of the road', 'Vehicle roof', 'Roadside only'],
  'answer': 0},
 {'id': 'rot_48',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The angle through which a banked road is inclined to the horizontal is called:',
  'options': ['Angle of banking', 'Angle of contact', 'Angle of friction only', 'Angular velocity'],
  'answer': 0},
 {'id': 'rot_49',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The purpose of banking a curved road is mainly to improve:',
  'options': ['Safety while taking turns', 'Vehicle mass', 'Engine power', 'Road temperature'],
  'answer': 0},
 {'id': 'rot_50',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For an ideal banked road neglecting friction, the horizontal component of normal reaction provides:',
  'options': ['Centripetal force', 'Weight', 'Tangential acceleration only', 'Centrifugal force'],
  'answer': 0},
 {'id': 'rot_51',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a banked road without friction, the safe-speed expression depends on:',
  'options': ['Radius and angle of banking', 'Vehicle mass only', 'Tyre colour', 'Engine power only'],
  'answer': 0},
 {'id': 'rot_52',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The notes state that safe speed on a banked road is independent of:',
  'options': ['Mass of the vehicle', 'Radius of curvature', 'Angle of banking', 'Gravitational acceleration'],
  'answer': 0},
 {'id': 'rot_53',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'If friction is available on a banked road, it can act:',
  'options': ['Along the inclined road surface', 'Only vertically upward', 'Only horizontally outward', 'Only toward the sky'],
  'answer': 0},
 {'id': 'rot_54',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'A conical pendulum consists of a bob moving in a:',
  'options': ['Horizontal circular path', 'Straight vertical line', 'Horizontal straight line', 'Parabolic path only'],
  'answer': 0},
 {'id': 'rot_55',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In a conical pendulum, the string makes an angle with the:',
  'options': ['Vertical', 'Horizontal only', 'Road surface', 'Radius of the Earth'],
  'answer': 0},
 {'id': 'rot_56',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The tension in a conical pendulum can be resolved into:',
  'options': ['Vertical and horizontal components',
              'Only horizontal components',
              'Only vertical components',
              'Tangential and radial velocities only'],
  'answer': 0},
 {'id': 'rot_57',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a conical pendulum, the vertical component of tension balances:',
  'options': ['Weight of the bob', 'Centripetal force', 'Friction', 'Angular acceleration'],
  'answer': 0},
 {'id': 'rot_58',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a conical pendulum, the horizontal component of tension provides:',
  'options': ['Centripetal force', 'Weight', 'Normal force from a road', 'Tangential acceleration only'],
  'answer': 0},
 {'id': 'rot_59',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In a conical pendulum, the centre of the circular path lies:',
  'options': ['On the vertical axis below the support', 'At the bob', 'At the end of the string only', 'Outside the plane of motion'],
  'answer': 0},
 {'id': 'rot_60',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'A simple pendulum consists of a bob connected to a support by a:',
  'options': ['Light, flexible, inextensible string', 'Heavy elastic rod', 'Rigid metal plate', 'Spring with variable length'],
  'answer': 0},
 {'id': 'rot_61',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The period of a simple pendulum in the small-angle model depends on its:',
  'options': ['Length and gravitational acceleration', 'Mass only', 'Colour and mass', 'Radius of bob only'],
  'answer': 0},
 {'id': 'rot_62',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In the vertical circular motion discussed in the notes, at the uppermost point the normal reaction may become:',
  'options': ['Zero at the limiting condition', 'Always infinite', 'Always equal to weight', 'Always negative'],
  'answer': 0},
 {'id': 'rot_63',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a body just maintaining contact at the uppermost point of a vertical circle, the normal reaction is:',
  'options': ['Zero', 'Maximum', 'Equal to 2mg', 'Equal to mg always'],
  'answer': 0},
 {'id': 'rot_64',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The limiting condition for contact at the top of a vertical circle is associated with:',
  'options': ['Minimum speed at the top', 'Maximum mass only', 'Zero radius', 'Zero gravitational acceleration'],
  'answer': 0},
 {'id': 'rot_65',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'At the bottom of a vertical circular path, the normal reaction on the body is generally:',
  'options': ['Greater than its weight for upward centripetal acceleration', 'Always zero', 'Always less than zero', 'Equal to mass only'],
  'answer': 0},
 {'id': 'rot_66',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The “Sphere of Death” stunt discussed in the notes involves:',
  'options': ['Circular motion inside a hollow sphere', 'Straight-line motion on a flat road', 'A stationary pendulum', 'Fluid flow'],
  'answer': 0},
 {'id': 'rot_67',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'A rigid body is one whose geometric shape remains:',
  'options': ['Unchanged under applied action', 'Always changing', 'Zero in size', 'Independent of mass only'],
  'answer': 0},
 {'id': 'rot_68',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In rotational motion of a rigid body, particles at different distances from the axis have:',
  'options': ['Different linear velocities', 'The same linear velocity in all cases', 'Zero velocity', 'Only radial velocity'],
  'answer': 0},
 {'id': 'rot_69',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In a rigid body rotating about a fixed axis, angular velocity of each particle is:',
  'options': ['The same', 'Different for every particle', 'Zero at all points', 'Equal to linear velocity'],
  'answer': 0},
 {'id': 'rot_70',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'An unbalanced torque produces:',
  'options': ['Rotational motion/angular acceleration', 'Only translational rest', 'Zero acceleration', 'Only gravitational force'],
  'answer': 0},
 {'id': 'rot_71',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Moment of inertia about an axis is the sum of:',
  'options': ['m r² for the particles', 'm/r for the particles', 'm r for the particles only', 'r²/m only'],
  'answer': 0},
 {'id': 'rot_72',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a continuous mass distribution, moment of inertia is written as:',
  'options': ['I = ∫r² dm', 'I = ∫r dm', 'I = ∫dm/r²', 'I = Mr'],
  'answer': 0},
 {'id': 'rot_73',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Moment of inertia depends on the:',
  'options': ['Mass distribution about the axis', 'Mass only and never distribution', 'Temperature only', 'Colour of the body'],
  'answer': 0},
 {'id': 'rot_74',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Moment of inertia represents resistance to change in:',
  'options': ['Rotational state', 'Chemical composition', 'Temperature', 'Volume only'],
  'answer': 0},
 {'id': 'rot_75',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In rotational motion, moment of inertia is analogous to:',
  'options': ['Mass in translational motion', 'Force in translation', 'Velocity in translation', 'Displacement in translation'],
  'answer': 0},
 {'id': 'rot_76',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The SI unit of moment of inertia is:',
  'options': ['kg m²', 'kg/m²', 'N/m', 'J/s'],
  'answer': 0},
 {'id': 'rot_77',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Radius of gyration is the distance from the axis at which the whole mass could be considered concentrated to give the same:',
  'options': ['Moment of inertia', 'Linear velocity', 'Angular displacement', 'Torque only'],
  'answer': 0},
 {'id': 'rot_78',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The relation between moment of inertia I, mass M and radius of gyration K is:',
  'options': ['I = MK²', 'I = M/K²', 'I = K/M', 'I = M²K'],
  'answer': 0},
 {'id': 'rot_79',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Radius of gyration depends on the:',
  'options': ['Distribution of mass about the axis', 'Total mass alone', 'Colour of the body', 'Temperature alone'],
  'answer': 0},
 {'id': 'rot_80',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a given body, moving more mass farther from the axis generally makes the moment of inertia:',
  'options': ['Larger', 'Smaller', 'Zero', 'Unchanged in every case'],
  'answer': 0},
 {'id': 'rot_81',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'If mass is distributed closer to the axis, the radius of gyration tends to be:',
  'options': ['Smaller', 'Larger', 'Infinite', 'Unrelated to distribution'],
  'answer': 0},
 {'id': 'rot_82',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Rotational kinetic energy of a rigid body is:',
  'options': ['(1/2)Iω²', 'Iω', 'I/ω²', '2Iω'],
  'answer': 0},
 {'id': 'rot_83',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Rotational kinetic energy is directly proportional to the square of:',
  'options': ['Angular velocity', 'Radius only', 'Mass only', 'Torque only'],
  'answer': 0},
 {'id': 'rot_84',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a rigid body rotating about a fixed axis, each particle has the same:',
  'options': ['Angular velocity', 'Linear velocity', 'Tangential speed', 'Distance from axis'],
  'answer': 0},
 {'id': 'rot_85',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For particles at different distances from the axis, tangential speed is related to angular speed by:',
  'options': ['v = rω', 'v = ω/r', 'v = r/ω', 'v = ω²/r'],
  'answer': 0},
 {'id': 'rot_86',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The kinetic energy of a rotating rigid body can be written as the sum of:',
  'options': ['Kinetic energies of its particles',
              'Only gravitational energies',
              'Only translational energies of the support',
              'Only potential energies'],
  'answer': 0},
 {'id': 'rot_87',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a rolling body, the motion involves simultaneous:',
  'options': ['Translation and rotation', 'Only translation', 'Only rotation', 'Oscillation and vibration only'],
  'answer': 0},
 {'id': 'rot_88',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In pure rolling, the centre of mass undergoes:',
  'options': ['Pure translational motion', 'Pure rotational motion about its own axis only', 'No motion', 'Vertical oscillation only'],
  'answer': 0},
 {'id': 'rot_89',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The kinetic energy of a rolling body is the sum of:',
  'options': ['Translational and rotational kinetic energies',
              'Only rotational kinetic energy',
              'Only potential energy',
              'Only heat energy'],
  'answer': 0},
 {'id': 'rot_90',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For pure rolling without slipping, the linear speed and angular speed satisfy:',
  'options': ['v = Rω', 'v = ω/R', 'v = R/ω', 'v = Rω²'],
  'answer': 0},
 {'id': 'rot_91',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a rolling rigid body, increasing its moment of inertia while keeping angular speed fixed increases its:',
  'options': ['Rotational kinetic energy', 'Mass automatically', 'Radius automatically', 'Gravitational acceleration'],
  'answer': 0},
 {'id': 'rot_92',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular momentum in the rotational analogy corresponds to:',
  'options': ['Linear momentum', 'Linear displacement', 'Linear acceleration', 'Mass'],
  'answer': 0},
 {'id': 'rot_93',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The rotational form of Newton’s second-law relation in the notes connects torque with:',
  'options': ['Moment of inertia and angular acceleration', 'Mass and linear displacement', 'Power and time only', 'Radius and mass only'],
  'answer': 0},
 {'id': 'rot_94',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The rotational equation analogous to F = ma is:',
  'options': ['τ = Iα', 'τ = I/α', 'τ = α/I', 'τ = Iα²'],
  'answer': 0},
 {'id': 'rot_95',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Angular momentum of a rigid body about a fixed axis is related to:',
  'options': ['Moment of inertia and angular velocity', 'Mass and linear displacement only', 'Force and time only', 'Radius and pressure'],
  'answer': 0},
 {'id': 'rot_96',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The rotational work done by a constant torque through angular displacement θ is:',
  'options': ['τθ', 'τ/θ', 'θ/τ', 'τ + θ'],
  'answer': 0},
 {'id': 'rot_97',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'Rotational power at angular velocity ω is:',
  'options': ['τω', 'τ/ω', 'ω/τ', 'τ + ω'],
  'answer': 0},
 {'id': 'rot_98',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'In uniform circular motion, the acceleration is directed toward the centre even though speed is:',
  'options': ['Constant', 'Zero', 'Increasing uniformly', 'Decreasing uniformly'],
  'answer': 0},
 {'id': 'rot_99',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'For a vehicle on an unbanked curved road, friction must provide the required:',
  'options': ['Centripetal force', 'Centrifugal force', 'Weight', 'Angular displacement'],
  'answer': 0},
 {'id': 'rot_100',
  'subject': 'Physics',
  'topic': 'Rotational Dynamics',
  'q': 'The chapter links safe vehicle turning with limiting:',
  'options': ['Friction and/or banking', 'Surface tension only', 'Electrical resistance', 'Fluid viscosity only'],
  'answer': 0}]

def get_all_questions():
    return QUESTIONS

def get_catalog():
    catalog={}
    for q in get_all_questions():
        subject=q.get("subject","General")
        topic=q.get("topic","General")
        catalog.setdefault(subject, set()).add(topic)
    return {s: sorted(list(ts)) for s,ts in sorted(catalog.items())}

def prepare_questions(raw_questions):
    """Make room-specific copies and shuffle answer options so the correct choice
    is not always in the same position. The answer index is updated safely."""
    prepared = []
    for original in raw_questions:
        q = copy.deepcopy(original)
        correct_text = q["options"][q["answer"]]
        random.shuffle(q["options"])
        q["answer"] = q["options"].index(correct_text)
        prepared.append(q)
    return prepared

def _deck_key(pool):
    """Create a stable key for a question pool so each topic gets its own deck."""
    return tuple(sorted(str(q.get("id", "")) for q in pool))


def _deal_random_questions(pool, amount):
    """Deal questions from a shuffled deck without immediate/recent repeats.

    Each subject/topic pool has its own deck. A question is removed from the deck
    when dealt and only becomes available again after that pool is exhausted.
    This gives much stronger randomization than random.sample() for repeated
    battles on the same topic.
    """
    if not pool:
        return []

    amount = max(1, min(int(amount), len(pool)))
    key = _deck_key(pool)
    pool_by_id = {str(q.get("id", "")): q for q in pool}

    deck = QUESTION_DECKS.get(key)
    if not deck or any(qid not in pool_by_id for qid in deck):
        deck = list(pool_by_id.keys())
        random.shuffle(deck)
        QUESTION_DECKS[key] = deck

    chosen_ids = []
    while len(chosen_ids) < amount:
        if not deck:
            # The complete pool has been used. Start a fresh random cycle.
            deck.extend(pool_by_id.keys())
            random.shuffle(deck)

        take = min(amount - len(chosen_ids), len(deck))
        chosen_ids.extend(deck[:take])
        del deck[:take]

    return [pool_by_id[qid] for qid in chosen_ids]


def choose_questions_from_selection(selections, amount, battle_mode):
    allq=get_all_questions()
    selected=[]
    wanted={(str(x.get("subject","")).strip(), str(x.get("topic","")).strip()) for x in (selections or [])}
    for q in allq:
        if (q.get("subject"), q.get("topic")) in wanted:
            selected.append(q)
    if not selected:
        return choose_questions("mixed", amount, battle_mode)

    amount=max(5, min(int(amount), len(selected)))
    chosen=_deal_random_questions(selected, amount)
    chosen=prepare_questions(chosen)
    return chosen, "Multiple Subjects" if len({q["subject"] for q in selected})>1 else selected[0]["subject"], "Multiple Topics" if len({(q["subject"],q["topic"]) for q in selected})>1 else selected[0]["topic"]


def load_progress():
    global players
    if not os.path.exists(SAVE_FILE):
        players = {}
        return
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            players = json.load(f)
    except Exception:
        players = {}

def save_progress():
    # Atomic save: prevents the progress file from being left half-written.
    tmp = SAVE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)
    os.replace(tmp, SAVE_FILE)

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000
    ).hex()
    return salt + "$" + digest

def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120000
        ).hex()
        return secrets.compare_digest(check, digest)
    except Exception:
        return False

def clean_username(name):
    return re.sub(r"[^A-Za-z0-9_]", "", str(name or "").strip())[:24]

def get_player(name):
    if name not in players:
        players[name] = {
            "password_hash": None,
            "xp": 0, "wins": 0, "battles": 0,
            "attempted": 0, "correct": 0, "accuracy": 0,
            "best_score": 0, "best_streak": 0,
            "win_streak": 0, "coins": 0, "level": 1,
            "achievements": [], "champion": False, "champion_wins": 0,
            "history": [], "session_wins": 0
        }
    else:
        # Keep old V6 progress files compatible.
        players[name].setdefault("password_hash", None)
        players[name].setdefault("xp", 0)
        players[name].setdefault("wins", 0)
        players[name].setdefault("battles", 0)
        players[name].setdefault("attempted", 0)
        players[name].setdefault("correct", 0)
        players[name].setdefault("accuracy", 0)
        players[name].setdefault("best_score", 0)
        players[name].setdefault("best_streak", 0)
        players[name].setdefault("win_streak", 0)
        players[name].setdefault("coins", 0)
        players[name].setdefault("level", max(1, players[name].get("xp", 0)//100 + 1))
        players[name].setdefault("achievements", [])
        players[name].setdefault("champion", False)
        players[name].setdefault("champion_wins", 0)
        players[name].setdefault("history", [])
        players[name].setdefault("session_wins", 0)
    return players[name]

def clean_name(name):
    return clean_username(name)

def generate_code():
    while True:
        c = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if c not in rooms:
            return c

def update_achievement(d, achievement):
    d.setdefault("achievements", [])
    if achievement not in d["achievements"]:
        d["achievements"].append(achievement)

def refresh_level(d):
    d["level"] = max(1, int(d.get("xp", 0)) // 100 + 1)

def apply_winner_rewards(d):
    d["coins"] = d.get("coins", 0) + 100
    d["win_streak"] = d.get("win_streak", 0) + 1
    d["champion"] = True
    d["champion_wins"] = d.get("champion_wins", 0) + 1
    update_achievement(d, "🏆 First Victory")
    update_achievement(d, "👑 Champion")
    if d["win_streak"] >= 3:
        update_achievement(d, "🔥 Unstoppable (3 Win Streak)")
    if d["win_streak"] >= 5:
        update_achievement(d, "🔥 Legendary (5 Win Streak)")
    if d.get("wins", 0) >= 5:
        update_achievement(d, "👑 5-Time Champion")
    refresh_level(d)

def make_player(name):
    return {
        "name": name,
        "score": 0,
        "correct": 0,
        "answered": 0,
        "answer_index": -1,
        "current_answer": None,
        "streak": 0,
        "best_streak": 0,
        "elimination_warning": False,
        "eliminated": False,
        "session_score": 0,
        "max_speed_bonus": 0,
        "rank_before": None
    }

def player_public_data(p):
    return {
        "name": p["name"],
        "score": p["score"],
        "correct": p["correct"],
        "answered": p["answered"],
        "answer_index": p["answer_index"],
        "streak": p["streak"],
        "best_streak": p["best_streak"],
        "elimination_warning": p["elimination_warning"],
        "eliminated": p["eliminated"],
        "session_score": p.get("session_score", 0)
    }

def public_room(room):
    out = {
        "code": room["code"],
        "host": room["host"],
        "players": [player_public_data(p) for p in room["players"]],
        "status": room["status"],
        "question_index": room["question_index"],
        "total_questions": len(room["questions"]),
        "question_started": room.get("question_started", 0),
        "subject": room["subject"],
        "topic": room["topic"],
        "selections": room.get("selections", []),
        "battle_mode": room.get("battle_mode", "classic"),
        "question_time": room.get("question_time", QUESTION_TIME),
        "is_final_question": room["question_index"] == len(room["questions"]) - 1 if room["questions"] else False,
        "chat": room.get("chat", [])[-100:],
        "dare": room.get("dare"),
        "dare_player": room.get("dare_player"),
        "dares_list": DARE_LIST,
        "rewards": room.get("rewards", {}),
        "winner": room.get("winner"),
        "finished_at": room.get("finished_at", 0),
        "intro_started": room.get("intro_started", 0),
        "intro_duration": room.get("intro_duration", 10),
        "session_battles": room.get("session_battles", 1),
        "session_battle": room.get("session_battle", 1),
        "session_scores": room.get("session_scores", {}),
        "session_stats": room.get("session_stats", {}),
        "battle_awards": room.get("battle_awards", []),
        "session_special_awards": room.get("session_special_awards", []),
        "session_champion": room.get("session_champion"),
        "session_finished": room.get("session_finished", False),
        "surprise": room.get("surprise"),
        "surprise_history": room.get("surprise_history", []),
        "session_awards": room.get("session_awards", []),
        "session_last_place": room.get("session_last_place")
    }
    if room["status"] == "playing" and room["question_index"] < len(room["questions"]):
        q = room["questions"][room["question_index"]]
        out["question"] = {"q": q["q"], "options": q["options"], "subject": q["subject"], "topic": q["topic"]}
    return out

def choose_questions(mode, amount, battle_mode):
    if mode == "halogen":
        pool = [q for q in QUESTIONS if q["subject"] == "Chemistry"]
        subject = "Chemistry"
        topic = "Halogen Derivatives"
    elif mode == "fluids":
        pool = [q for q in QUESTIONS if q["subject"] == "Physics"]
        subject = "Physics"
        topic = "Mechanical Properties of Fluids"
    else:
        pool = QUESTIONS[:]
        subject = "Mixed"
        topic = "Halogen + Fluids"

    amount = max(5, min(int(amount), len(pool)))

    return prepare_questions(_deal_random_questions(pool, amount)), subject, topic

def finish_room(room):
    if room.get("status") == "finished":
        return

    hidden_names = {str(x).strip().lower() for x in HALL_OF_FAME_HIDDEN_NAMES}
    is_tournament = room.get("battle_mode") == "tournament"
    ranked = sorted(room["players"], key=lambda p: (p["score"], p["correct"]), reverse=True)
    room["rewards"] = {}
    winner_name = ranked[0]["name"] if ranked else None

    # Testing accounts remain hidden from the public Hall of Fame, but are fully eligible in Tournament Mode for testing.
    eligible_ranked = ranked if is_tournament else [p for p in ranked if p["name"].strip().lower() not in hidden_names]
    awards = []
    # Tournament awards are intentionally NOT calculated per battle. They are based
    # on the player's accumulated performance across the whole session and are
    # revealed only after the final tournament battle.
    if not is_tournament and eligible_ranked:
        top_acc = max((p["correct"] / p["answered"] * 100) if p["answered"] else 0 for p in eligible_ranked)
        top_streak = max((p.get("best_streak", 0) for p in eligible_ranked), default=0)
        top_speed = max((p.get("max_speed_bonus", 0) for p in eligible_ranked), default=0)
        for p in eligible_ranked:
            acc = (p["correct"] / p["answered"] * 100) if p["answered"] else 0
            if acc == top_acc and top_acc > 0:
                awards.append({"name": p["name"], "award": "🧠 Brain Master", "reason": f"{round(acc)}% accuracy"})
            if p.get("best_streak", 0) == top_streak and top_streak >= 3:
                awards.append({"name": p["name"], "award": "🔥 Streak King", "reason": f"{top_streak} streak"})
            if p.get("max_speed_bonus", 0) == top_speed and top_speed >= 3:
                awards.append({"name": p["name"], "award": "⚡ Speed Demon", "reason": "Lightning-fast answer"})

    room["battle_awards"] = awards if not is_tournament else []
    for pos, rp in enumerate(ranked):
        d = get_player(rp["name"])
        d["xp"] += rp["score"]
        d["battles"] += 1
        d["attempted"] += rp["answered"]
        d["correct"] += rp["correct"]
        d["best_score"] = max(d["best_score"], rp["score"])
        d["best_streak"] = max(d.get("best_streak", 0), rp["best_streak"])
        if d["attempted"]:
            d["accuracy"] = round(d["correct"] / d["attempted"] * 100, 1)
        rp["session_score"] = rp.get("session_score", 0) + rp["score"]
        room.setdefault("session_scores", {})[rp["name"]] = rp["session_score"]
        if is_tournament:
            ss = room.setdefault("session_stats", {}).setdefault(rp["name"], {
                "correct": 0, "answered": 0, "best_streak": 0,
                "max_speed_bonus": 0, "battle_wins": 0, "battles_played": 0
            })
            ss["correct"] += rp.get("correct", 0)
            ss["answered"] += rp.get("answered", 0)
            ss["best_streak"] = max(ss.get("best_streak", 0), rp.get("best_streak", 0))
            ss["max_speed_bonus"] = max(ss.get("max_speed_bonus", 0), rp.get("max_speed_bonus", 0))
            ss["battles_played"] += 1
            if pos == 0:
                ss["battle_wins"] += 1
        if pos == 0:
            d["wins"] += 1
            apply_winner_rewards(d)
            room["rewards"][rp["name"]] = {
                "xp_bonus": 0, "coins": 100, "win_streak": d["win_streak"],
                "level": d["level"], "title": "👑 Champion"
            }
        else:
            d["win_streak"] = 0
            d["champion"] = False
            refresh_level(d)

        acc = round((rp["correct"] / rp["answered"] * 100), 1) if rp["answered"] else 0
        my_awards = [a["award"] for a in awards if a["name"].lower() == rp["name"].lower()]
        d.setdefault("history", []).append({
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "topic": room.get("topic", "Mixed"),
            "score": rp["score"], "position": pos + 1,
            "correct": rp["correct"], "answered": rp["answered"],
            "accuracy": acc, "best_streak": rp["best_streak"],
            "awards": my_awards,
            "session": room.get("session_battle", 1)
        })
        d["history"] = d["history"][-30:]

    is_final_session = (not is_tournament) or (room.get("session_battle", 1) >= room.get("session_battles", 1))

    # Dares happen ONLY once, after the complete tournament session.
    # For a normal single battle, the existing end-of-battle dare remains.
    room["dare"] = None
    room["dare_player"] = None
    if is_final_session and room.get("players"):
        if is_tournament:
            totals = list(room.get("session_scores", {}).items())
            totals.sort(key=lambda x: x[1])
            if totals:
                room["session_last_place"] = totals[0][0]
                room["dare_player"] = totals[0][0]
                room["dare"] = random.choice(DARE_LIST)
        elif ranked:
            real_ranked = [p for p in ranked if p["name"].strip().lower() not in hidden_names]
            if real_ranked:
                room["dare_player"] = real_ranked[-1]["name"]
                room["dare"] = random.choice(DARE_LIST)

    room["winner"] = winner_name
    room["status"] = "finished"
    room["finished_at"] = time.time()

    if is_final_session:
        room["session_finished"] = True
        totals = list(room.get("session_scores", {}).items()) if is_tournament else [(n, v) for n, v in room.get("session_scores", {}).items() if n.strip().lower() not in hidden_names]
        totals.sort(key=lambda x: x[1], reverse=True)
        room["session_champion"] = totals[0][0] if totals else None
        room["session_awards"] = []
        room["session_special_awards"] = []
        if totals:
            champ = get_player(totals[0][0])
            champ["session_wins"] = champ.get("session_wins", 0) + 1
            update_achievement(champ, "🏟️ Session Champion")
            room["session_awards"].append({"name": totals[0][0], "award": "👑 Session Champion", "value": totals[0][1]})

        if is_tournament:
            # Overall-session special awards: use cumulative tournament statistics,
            # never a single battle's result.
            session_stats = room.get("session_stats", {})
            ranked_names = [n for n, _ in totals]
            session_special = []
            valid_stats = [(n, session_stats.get(n, {})) for n in ranked_names if n in session_stats]
            if valid_stats:
                def acc_of(item):
                    st=item[1]; return (st.get("correct",0)/st.get("answered",0)*100) if st.get("answered",0) else 0
                top_acc=max(acc_of(x) for x in valid_stats)
                top_streak=max(st.get("best_streak",0) for _,st in valid_stats)
                top_speed=max(st.get("max_speed_bonus",0) for _,st in valid_stats)
                for n, st in valid_stats:
                    acc=acc_of((n,st))
                    if top_acc > 0 and acc == top_acc:
                        session_special.append({"name":n,"award":"🧠 Brain Master","reason":f"{round(acc)}% tournament accuracy"})
                    if top_streak >= 3 and st.get("best_streak",0) == top_streak:
                        session_special.append({"name":n,"award":"🔥 Streak King","reason":f"{top_streak} best streak across the tournament"})
                    if top_speed >= 3 and st.get("max_speed_bonus",0) == top_speed:
                        session_special.append({"name":n,"award":"⚡ Speed Demon","reason":"Fastest answers across the tournament"})
                room["session_special_awards"] = session_special
                room["session_awards"].extend(session_special)
                # Attach the final-session awards to the player's latest history entry.
                for a in session_special:
                    for dname in [a["name"]]:
                        account=get_player(dname)
                        if account.get("history"):
                            account["history"][-1].setdefault("awards", []).append(a["award"])
    else:
        room["session_finished"] = False
        room["session_champion"] = None
        room["session_awards"] = []
        room["session_special_awards"] = []

    save_progress()

def advance_room(room):
    if room["status"] != "playing":
        return
    
    # Check for elimination warning logic before proceeding
    if room["question_index"] < len(room["questions"]) - 1:
        ranked = sorted(room["players"], key=lambda p: (p["score"], p["correct"]))
        if ranked:
            lowest_score = ranked[0]["score"]
            for p in room["players"]:
                p["elimination_warning"] = (p["score"] == lowest_score)
    
    room["question_index"] += 1
    if room["question_index"] >= len(room["questions"]):
        finish_room(room)
        return
    room["question_started"] = time.time()
    for p in room["players"]:
        p["answer_index"] = -1
        p["current_answer"] = None



# ============================================================
# MULTIPLAYER BOSS BATTLE
# ============================================================
BOSS_MAX_HP = 1000
BOSS_DAMAGE = 50
BOSS_FAST_BONUS = 20

def ensure_boss(room):
    """Create/reset the cooperative boss state for a room."""
    if "boss" not in room:
        room["boss"] = {
            "name": "StudyBattle Boss",
            "max_hp": BOSS_MAX_HP,
            "hp": BOSS_MAX_HP,
            "active": False,
            "defeated": False,
            "damage": {},
            "started_at": None
        }
    return room["boss"]

def boss_start(room):
    boss = ensure_boss(room)
    boss["hp"] = boss["max_hp"]
    boss["active"] = True
    boss["defeated"] = False
    boss["damage"] = {}
    boss["started_at"] = time.time()
    return boss

def boss_deal_damage(room, player_name, fast=False):
    boss = ensure_boss(room)
    if not boss["active"] or boss["defeated"]:
        return boss

    amount = BOSS_DAMAGE + (BOSS_FAST_BONUS if fast else 0)
    boss["hp"] = max(0, boss["hp"] - amount)
    boss["damage"][player_name] = boss["damage"].get(player_name, 0) + amount

    if boss["hp"] <= 0:
        boss["hp"] = 0
        boss["active"] = False
        boss["defeated"] = True

    return boss

@app.route("/api/boss_state", methods=["POST"])
def api_boss_state():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()

    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify({"ok": False, "error": "Room not found"}), 404

        boss = ensure_boss(room)
        return jsonify({"ok": True, "boss": boss})

@app.route("/api/boss_start", methods=["POST"])
def api_boss_start():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()

    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify({"ok": False, "error": "Room not found"}), 404

        # Boss can be started by the host or when the battle begins.
        boss = boss_start(room)
        room["game_mode"] = "boss"
        return jsonify({"ok": True, "boss": boss})

@app.route("/api/boss_attack", methods=["POST"])
def api_boss_attack():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    player = str(data.get("name", "")).strip()
    fast = bool(data.get("fast", False))

    if not player:
        return jsonify({"ok": False, "error": "Player name required"}), 400

    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify({"ok": False, "error": "Room not found"}), 404

        if player not in players or players[player].get("room") != code:
            return jsonify({"ok": False, "error": "Player is not in this room"}), 403

        boss = boss_deal_damage(room, player, fast=fast)
        return jsonify({
            "ok": True,
            "boss": boss,
            "defeated": boss["defeated"]
        })


@app.route("/api/features", methods=["GET"])
def api_features_ultimate():
    return jsonify({
        "max_players": 15,
        "question_counts": [5, 10, 15, 20, 30],
        "features": ULTIMATE_FEATURES
    })


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = clean_username(data.get("username"))
    password = str(data.get("password") or "")

    if len(username) < 3:
        return jsonify(success=False, message="Username must be at least 3 characters.")
    if len(password) < 4:
        return jsonify(success=False, message="Password must be at least 4 characters.")

    with lock:
        account = players.get(username)

        # If this username already existed in old V6, preserve its progress
        # and let the owner attach a password to it.
        if account:
            get_player(username)
            if account.get("password_hash"):
                return jsonify(success=False, message="Username already exists. Please login.")
            account["password_hash"] = hash_password(password)
        else:
            get_player(username)
            players[username]["password_hash"] = hash_password(password)

        save_progress()
        safe = dict(players[username])
        safe.pop("password_hash", None)

    return jsonify(success=True, username=username, player=safe)


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = clean_username(data.get("username"))
    password = str(data.get("password") or "")

    with lock:
        account = players.get(username)

        if not account:
            return jsonify(success=False, message="Account not found. Tap Create Account.")
        if not account.get("password_hash"):
            return jsonify(success=False, message="This is an old V6 account. Tap Create Account once to set its password.")
        if not verify_password(password, account["password_hash"]):
            return jsonify(success=False, message="Wrong username or password.")

        safe = dict(account)
        safe.pop("password_hash", None)

    return jsonify(success=True, username=username, player=safe)


@app.route("/api/profile")
def profile():
    username = clean_username(request.args.get("username"))

    with lock:
        account = players.get(username)
        if not account:
            return jsonify(success=False, message="Player not found.")

        safe = dict(account)
        safe.pop("password_hash", None)

    return jsonify(success=True, username=username, player=safe)



@app.route("/api/catalog")
def api_catalog():
    with lock:
        return jsonify(success=True, catalog=get_catalog())


TOURNAMENT_SURPRISES = [
    {"id":"double_xp", "name":"💎 DOUBLE XP", "description":"All points earned this battle are doubled.", "multiplier":2, "question_time":QUESTION_TIME},
    {"id":"speed_round", "name":"⚡ SPEED ROUND", "description":"Questions have only 10 seconds each.", "multiplier":1, "question_time":10},
    {"id":"streak_frenzy", "name":"🔥 STREAK FRENZY", "description":"Streak bonuses are doubled this battle.", "multiplier":1, "question_time":QUESTION_TIME},
    {"id":"accuracy_boost", "name":"🎯 ACCURACY BOOST", "description":"Every correct answer gets +2 bonus XP.", "multiplier":1, "question_time":QUESTION_TIME},
    {"id":"comeback", "name":"🚀 COMEBACK ROUND", "description":"Players outside 1st place get +2 bonus XP for each correct answer.", "multiplier":1, "question_time":QUESTION_TIME}
]

def choose_tournament_surprise(used_ids=None, final_battle=False):
    """Fresh surprise every tournament battle; Comeback only on the final battle."""
    if final_battle:
        return next(x for x in TOURNAMENT_SURPRISES if x["id"] == "comeback").copy()
    used_ids = set(used_ids or [])
    pool = [x for x in TOURNAMENT_SURPRISES if x["id"] != "comeback"]
    available = [x for x in pool if x["id"] not in used_ids]
    if not available:
        available = pool[:]
    return random.choice(available).copy()

@app.route("/api/create_room", methods=["POST"])
def create_room():
    data = request.get_json() or {}
    name = clean_name(data.get("name"))
    mode = str(data.get("mode", "mixed")).lower()
    battle_mode = str(data.get("battle_mode", "classic")).lower()
    selections = data.get("selections", [])
    if not isinstance(selections, list):
        selections = []
    
    if not name:
        return jsonify(success=False, message="Please login first.")
    with lock:
        if name not in players:
            return jsonify(success=False, message="Account not found. Please login.")
    if mode not in {"mixed", "halogen", "fluids"}:
        mode = "mixed"
    if battle_mode not in {"classic", "sudden_death", "streak", "tournament"}:
        battle_mode = "classic"
        
    try:
        amount = int(data.get("amount", 10))
    except Exception:
        amount = 10
        
    q_time = QUESTION_TIME
    # Tournament mode is a session of multiple battles with a random surprise each battle.
    if battle_mode == "tournament":
        session_battles = 3
    try:
        session_battles = max(1, min(5, int(data.get("session_battles", 1))))
    except Exception:
        session_battles = 1

    with lock:
        code = generate_code()
        if selections:
            qs, subject, topic = choose_questions_from_selection(selections, amount, battle_mode)
        else:
            qs, subject, topic = choose_questions(mode, amount, battle_mode)
        if not qs:
            return jsonify(success=False, message="No questions found for the selected topics.")
        rooms[code] = {
            "code": code,
            "host": name,
            "players": [make_player(name)],
            "status": "waiting",
            "question_index": 0,
            "questions": qs,
            "question_started": 0,
            "dare": None,
            "dare_player": None,
            "subject": subject,
            "topic": topic,
            "selections": selections,
            "battle_mode": battle_mode,
            "question_time": q_time,
            "created": time.time(),
            "chat": [{"name": "StudyBattle", "text": f"Room created by {name} 👋", "time": time.time(), "system": True}],
            "session_battles": session_battles, "session_battle": 1, "session_scores": {},
            "session_stats": {},
            "battle_awards": [], "session_special_awards": [], "session_finished": False, "session_champion": None,
            "session_last_place": None,
            "intro_duration": 10,
            "surprise_history": [],
            "surprise": None
        }
    return jsonify(success=True, code=code, amount=len(qs), subject=subject, topic=topic, session_battles=session_battles)

@app.route("/api/join_room", methods=["POST"])
def join_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    if not name or not code:
        return jsonify(success=False, message="Login and enter a room code.")
    with lock:
        if name not in players:
            return jsonify(success=False, message="Account not found. Please login.")
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["status"] != "waiting":
            return jsonify(success=False, message="Battle already started.")
        if len(room["players"]) >= MAX_PLAYERS:
            return jsonify(success=False, message="Room is full.")
        if any(p["name"].lower() == name.lower() for p in room["players"]):
            return jsonify(success=False, message="Name already used.")
        room["players"].append(make_player(name))
        room.setdefault("chat", []).append({"name": "StudyBattle", "text": f"{name} joined the room! 👋", "time": time.time(), "system": True})
        room["chat"] = room["chat"][-100:]
    return jsonify(success=True)

@app.route("/api/cancel_room", methods=["POST"])
def cancel_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["host"].lower() != name.lower():
            return jsonify(success=False, message="Only the host can cancel the room.")
        rooms.pop(code, None)
    return jsonify(success=True)

@app.route("/api/start_room", methods=["POST"])
def start_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["host"].lower() != name.lower():
            return jsonify(success=False, message="Only the host can start the battle.")
        if len(room["players"]) < MIN_PLAYERS:
            return jsonify(success=False, message="Need at least 2 players.")
        if room.get("status") == "finished" and room.get("session_finished"):
            return jsonify(success=False, message="This session is already complete.")
        if room.get("status") == "finished":
            room["session_battle"] = room.get("session_battle", 1) + 1
            if room["session_battle"] > room.get("session_battles", 1):
                room["session_finished"] = True
                return jsonify(success=False, message="Session complete.")
            if room.get("selections"):
                qs, subject, topic = choose_questions_from_selection(room["selections"], len(room["questions"]), room.get("battle_mode", "classic"))
            else:
                qs, subject, topic = choose_questions("mixed", len(room["questions"]), room.get("battle_mode", "classic"))
            room["questions"] = qs
            room["subject"], room["topic"] = subject, topic
            room["dare"] = None; room["dare_player"] = None; room["battle_awards"] = []
            for p in room["players"]:
                p.update({"score":0,"correct":0,"answered":0,"answer_index":-1,"current_answer":None,"streak":0,"best_streak":0,"elimination_warning":False,"eliminated":False,"max_speed_bonus":0})
        # Every tournament battle gets a fresh surprise. Final battle is always Comeback Round.
        if room.get("battle_mode") == "tournament":
            used = room.get("surprise_history", [])
            battle_no = room.get("session_battle", 1)
            total_battles = room.get("session_battles", 3)
            is_final_battle = battle_no >= total_battles
            room["surprise"] = choose_tournament_surprise(used, final_battle=is_final_battle)
            room["surprise_history"] = used + [room["surprise"].get("id")]
            room["question_time"] = room["surprise"].get("question_time", QUESTION_TIME)
        else:
            room["surprise"] = None
            room["question_time"] = QUESTION_TIME
        # Synchronized cinematic battle intro before each session battle.
        room["status"] = "intro"
        room["question_index"] = 0
        room["intro_started"] = time.time()
        room["question_started"] = 0
    return jsonify(success=True)

@app.route("/api/chat", methods=["POST"])
def send_chat():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    text = str(data.get("text", "")).strip()
    if not code or not name:
        return jsonify(success=False, message="Room and player are required.")
    if not text:
        return jsonify(success=False, message="Type a message first.")
    if len(text) > 240:
        return jsonify(success=False, message="Message is too long. Keep it under 240 characters.")
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if not any(p["name"].lower() == name.lower() for p in room["players"]):
            return jsonify(success=False, message="You are not in this room.")
        now = time.time()
        recent = [m for m in room.get("chat", []) if m.get("name", "").lower() == name.lower() and now - m.get("time", 0) < 8]
        if len(recent) >= 5:
            return jsonify(success=False, message="Slow down a little — chat is rate limited.")
        # Strip control characters; HTML escaping is also applied client-side.
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        room.setdefault("chat", []).append({"name": name, "text": text, "time": now, "system": False})
        room["chat"] = room["chat"][-100:]
    return jsonify(success=True)


@app.route("/api/room")
def api_room():
    code = request.args.get("code", "").strip().upper()
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["status"] == "intro":
            if time.time() - room.get("intro_started", time.time()) >= room.get("intro_duration", 10):
                room["status"] = "playing"
                room["question_started"] = time.time()
                for p in room["players"]:
                    p["answer_index"] = -1
                    p["current_answer"] = None
        if room["status"] == "playing":
            active_players = [p for p in room["players"] if not p.get("eliminated", False)]
            everyone = all(p["answer_index"] == room["question_index"] for p in active_players)
            timeout = time.time() - room["question_started"] >= room.get("question_time", QUESTION_TIME)
            if everyone or timeout:
                advance_room(room)
        return jsonify(success=True, room=public_room(room))

@app.route("/api/answer_room", methods=["POST"])
def answer_room():
    data = request.get_json() or {}
    code = str(data.get("code", "")).strip().upper()
    name = clean_name(data.get("name"))
    try:
        answer = int(data.get("answer", -1))
        qi = int(data.get("question_index", -1))
    except Exception:
        return jsonify(success=False, message="Invalid answer.")
        
    with lock:
        room = rooms.get(code)
        if not room:
            return jsonify(success=False, message="Room not found.")
        if room["status"] != "playing":
            return jsonify(success=False, message="Battle is not active.")
        if qi != room["question_index"]:
            return jsonify(success=False, message="Question changed.")
        if answer < 0 or answer > 3:
            return jsonify(success=False, message="Invalid option.")
            
        q_time = room.get("question_time", QUESTION_TIME)
        elapsed = time.time() - room["question_started"]
        if elapsed > q_time:
            advance_room(room)
            return jsonify(success=False, message="Time expired.")
            
        player = next((p for p in room["players"] if p["name"].lower() == name.lower()), None)
        if not player:
            return jsonify(success=False, message="Player not found.")
        if player.get("eliminated", False):
            return jsonify(success=False, message="You are eliminated from answering!")
        if player["answer_index"] == qi:
            return jsonify(success=False, message="Already answered.")
            
        q = room["questions"][qi]
        player["answer_index"] = qi
        player["current_answer"] = answer
        player["answered"] += 1
        correct = (answer == q["answer"])
        
        gained_points = 0
        speed_bonus = 0
        streak_bonus = 0
        
        is_final = (qi == len(room["questions"]) - 1)
        base_multiplier = 3 if is_final else 1
        surprise = room.get("surprise") or {}
        if room.get("battle_mode") == "tournament":
            if surprise.get("id") == "double_xp":
                base_multiplier *= 2

        if correct:
            player["correct"] += 1
            player["streak"] += 1
            player["best_streak"] = max(player["best_streak"], player["streak"])
            
            # Speed Bonus Calculation
            if elapsed <= 3.0:
                speed_bonus = 3
            elif elapsed <= 7.0:
                speed_bonus = 2
            elif elapsed <= 15.0:
                speed_bonus = 1
                
            # Streak Bonus Calculation
            if room.get("battle_mode") == "streak":
                streak_bonus = player["streak"] * 2
            elif player["streak"] >= 5:
                streak_bonus = 3
            elif player["streak"] >= 3:
                streak_bonus = 2
            elif player["streak"] >= 2:
                streak_bonus = 1
                
            if room.get("battle_mode") == "tournament" and surprise.get("id") == "streak_frenzy":
                streak_bonus *= 2
            gained_points = (BASE_POINTS + speed_bonus + streak_bonus) * base_multiplier
            if room.get("battle_mode") == "tournament" and surprise.get("id") == "accuracy_boost":
                gained_points += 2
            if room.get("battle_mode") == "tournament" and surprise.get("id") == "comeback":
                live_scores = sorted([x.get("score", 0) for x in room["players"]], reverse=True)
                if live_scores and player.get("score", 0) < live_scores[0]:
                    gained_points += 2
            player["score"] += gained_points
            player["max_speed_bonus"] = max(player.get("max_speed_bonus", 0), speed_bonus)
        else:
            player["streak"] = 0
            if room.get("battle_mode") == "sudden_death":
                player["eliminated"] = True
                
        return jsonify(
            success=True, 
            correct=correct, 
            score=player["score"], 
            points=gained_points,
            speed_bonus=speed_bonus,
            streak=player["streak"],
            correct_answer_index=q["answer"],
            correct_answer=q["options"][q["answer"]]
        )

@app.route("/api/dashboard")
def dashboard():
    with lock:
        ranking = []
        for n, d in players.items():
            # Testing accounts remain usable, but do not affect the public Hall of Fame.
            if str(n).strip().lower() in HALL_OF_FAME_HIDDEN_NAMES:
                continue
            refresh_level(d)
            safe = {"name": n, **d}
            safe.pop("password_hash", None)
            ranking.append(safe)
        ranking.sort(key=lambda x: (x.get("wins", 0), x.get("win_streak", 0), x.get("xp", 0)), reverse=True)
        return jsonify(success=True, players=ranking)

def room_cleanup():
    while True:
        time.sleep(60)
        now = time.time()
        with lock:
            for code, room in list(rooms.items()):
                if now - room.get("created", now) > 3600:
                    rooms.pop(code, None)

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>StudyBattle V6</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;font-family:Inter,Arial,sans-serif;background:radial-gradient(circle at top,#18244b,#090d1d 48%,#050711);color:#f8fafc}.container{max-width:760px;margin:auto;padding:14px}.hidden{display:none!important}.screen{animation:in .25s ease}@keyframes in{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}.brand{text-align:center;padding:16px 0 8px}.logo{font-size:40px;font-weight:1000;letter-spacing:-2px}.logo span{color:#38bdf8}.tag{color:#94a3b8;margin-top:4px}.card{background:rgba(15,23,42,.87);border:1px solid #1e293b;border-radius:22px;padding:19px;margin-top:13px;box-shadow:0 18px 55px #0005;backdrop-filter:blur(12px)}.title{font-size:24px;font-weight:900}.muted{color:#94a3b8}input,select{width:100%;padding:15px;margin-top:10px;border-radius:13px;border:1px solid #334155;background:#0b1120;color:white;font-size:16px;outline:none}input:focus,select:focus{border-color:#38bdf8}button{width:100%;padding:15px;margin-top:10px;border:0;border-radius:13px;background:linear-gradient(135deg,#2563eb,#06b6d4);color:white;font-weight:900;font-size:16px;cursor:pointer}button:disabled{opacity:.6}.secondary{background:#1e293b}.danger-btn{background:linear-gradient(135deg,#e11d48,#9f1239)}.modegrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px}.mode{padding:13px 12px;text-align:left;border:1px solid #334155;border-radius:15px;background:linear-gradient(180deg,#111827,#0b1120);font-weight:900;cursor:pointer;transition:.18s;min-height:78px}.mode:hover{transform:translateY(-1px);border-color:#475569}.mode.active{border-color:#38bdf8;background:linear-gradient(135deg,#172554,#0e7490);box-shadow:0 0 0 1px #38bdf855,0 8px 24px #0005}.mode .modeicon{font-size:22px;display:block;margin-bottom:4px}.mode .modename{display:block;font-size:14px}.mode .modesub{display:block;color:#94a3b8;font-size:11px;font-weight:700;margin-top:3px}.mode.active .modesub{color:#bae6fd}.roomcode{text-align:center;font-size:40px;font-weight:1000;letter-spacing:7px;color:#38bdf8;margin:10px}.row,.rank{display:flex;align-items:center;justify-content:space-between;background:#111827;border-radius:12px;padding:12px;margin-top:7px}.score{color:#38bdf8;font-weight:900}.badge{font-size:10px;padding:4px 7px;border-radius:999px;background:#164e63;color:#67e8f9;margin-left:5px}.warning-badge{background:#881337;color:#fda4af;font-size:10px;padding:3px 6px;border-radius:6px;margin-left:6px;font-weight:bold}.battlehead{display:flex;justify-content:space-between;align-items:center}.timer{width:62px;height:62px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#111827;border:4px solid #38bdf8;font-size:23px;font-weight:1000}.timer.danger{border-color:#fb7185;color:#fb7185}.q{font-size:24px;line-height:1.35;font-weight:900;margin:8px 0 16px}.opt{text-align:left;background:#111827;border:1px solid #334155}.opt:hover{border-color:#38bdf8;background:#172554}.correct{border:2px solid #22c55e!important;background:#16653455!important}.wrong{border:2px solid #fb7185!important;background:#7f1d1d55!important}.feedback{position:fixed;z-index:9;left:50%;top:50%;transform:translate(-50%,-50%);padding:24px;min-width:240px;text-align:center;border:2px solid;border-radius:20px;background:#0f172af5;box-shadow:0 20px 70px #0009}.feedback.good{border-color:#22c55e}.feedback.bad{border-color:#fb7185}.feedback b{font-size:28px}.resulticon{text-align:center;font-size:65px}.resulttitle{text-align:center;font-size:30px;font-weight:1000}.podium .row:first-child{border:1px solid #facc15;background:#4b3b0050}.dare{padding:22px;margin-top:14px;border-radius:20px;text-align:center;background:linear-gradient(135deg,#3b0764,#701a75);border:2px solid #e879f9}.darelabel{font-size:29px;font-weight:1000}.daretext{font-size:19px;font-weight:700;line-height:1.45;margin-top:12px}.small{font-size:12px;color:#64748b;margin-top:8px}.topiccatalog{margin-top:10px}.subjectbox{background:#0b1120;border:1px solid #1e293b;border-radius:14px;padding:10px;margin-top:8px}.subjecttitle{font-weight:900;color:#38bdf8;margin-bottom:6px}.topiccheck{display:flex;align-items:center;gap:8px;padding:8px;border-radius:9px;cursor:pointer}.topiccheck:hover{background:#111827}.topiccheck input{width:auto;margin:0}.topiccheck span{font-size:14px}.statsgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:12px}.statbox{background:#0b1120;border:1px solid #1e293b;border-radius:10px;padding:8px;text-align:center}.statval{font-size:16px;font-weight:900;color:#38bdf8}.statlbl{font-size:10px;color:#64748b}.chatbox{margin-top:12px}.chatmessages{height:220px;overflow-y:auto;background:#080d1a;border:1px solid #1e293b;border-radius:14px;padding:10px}.chatmsg{padding:7px 9px;margin-bottom:6px;background:#111827;border-radius:10px;word-break:break-word}.chatmsg .chatname{font-weight:900;color:#67e8f9;font-size:12px}.chatmsg .chattime{font-size:9px;color:#64748b;margin-left:6px}.chatmsg .chattext{margin-top:2px;font-size:13px;line-height:1.35}.chatform{display:flex;gap:7px;margin-top:8px}.chatform input{margin-top:0;flex:1}.chatform button{width:auto;margin-top:0;padding:12px 16px}.chat-empty{color:#64748b;text-align:center;padding:55px 8px;font-size:13px}@media(max-width:480px){.logo{font-size:34px}.q{font-size:21px}.roomcode{font-size:32px;letter-spacing:5px}.modegrid{grid-template-columns:1fr}.card{padding:16px}.statsgrid{grid-template-columns:repeat(2,1fr)}}
.session-champion-overlay{position:fixed;inset:0;z-index:220;background:radial-gradient(circle at 50% 42%,rgba(250,204,21,.2),rgba(2,6,23,.96) 58%);backdrop-filter:blur(12px);display:flex;align-items:center;justify-content:center;overflow:hidden}.session-champion-card{position:relative;width:min(94vw,620px);padding:42px 24px;text-align:center;border:3px solid #facc15;border-radius:32px;background:linear-gradient(145deg,#1e1b4b,#172554 45%,#3b0764);box-shadow:0 0 35px #facc1566,0 0 120px #facc1533,0 30px 120px #000d;animation:championBoom .8s cubic-bezier(.16,1.4,.3,1)}.champion-crown{font-size:92px;line-height:1;animation:championCrown .9s ease-in-out infinite}.champion-kicker{font-size:16px;letter-spacing:5px;font-weight:1000;color:#fde68a;margin-top:12px}.champion-heading{font-size:42px;font-weight:1000;letter-spacing:-1.5px;margin-top:8px;text-shadow:0 0 25px #facc1599}.champion-name{font-size:44px;font-weight:1000;color:#fef08a;margin-top:10px;word-break:break-word;text-shadow:0 0 30px #facc15cc}.champion-sub{font-size:18px;font-weight:900;color:#e2e8f0;margin-top:10px}.meow-badge{display:inline-block;margin-top:18px;padding:9px 16px;border-radius:999px;background:#facc1522;border:1px solid #facc1577;color:#fde68a;font-weight:1000;letter-spacing:1px}.champion-flash{position:absolute;inset:0;background:#fff7;opacity:0;pointer-events:none;animation:championFlash .45s ease-out}.champion-shockwave{position:absolute;left:50%;top:50%;width:50px;height:50px;border:4px solid #facc15;border-radius:50%;transform:translate(-50%,-50%);animation:shockwave 1.1s ease-out infinite;pointer-events:none}@keyframes championBoom{0%{opacity:0;transform:scale(.35) rotate(-2deg)}65%{transform:scale(1.05)}100%{opacity:1;transform:scale(1)}}@keyframes championCrown{0%,100%{transform:translateY(0) rotate(-3deg) scale(1)}50%{transform:translateY(-12px) rotate(3deg) scale(1.08)}}@keyframes championFlash{0%{opacity:.8}100%{opacity:0}}@keyframes shockwave{0%{width:50px;height:50px;opacity:.8}100%{width:900px;height:900px;opacity:0}}.result-actions{border-top:1px solid #1e293b}.battle-result-overlay{position:fixed;inset:0;z-index:100;background:rgba(2,6,23,.82);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;overflow:hidden}.battle-result-card{position:relative;width:min(92vw,520px);padding:34px 24px;text-align:center;border:2px solid #facc15;border-radius:28px;background:linear-gradient(145deg,#111827,#172554 55%,#3b0764);box-shadow:0 0 0 1px #facc1533,0 25px 100px #000b;animation:winnerPop .65s cubic-bezier(.2,1.5,.4,1)}.battle-result-card .trophy{font-size:76px;animation:trophyBounce 1s ease-in-out infinite}.battle-result-card .congrats{font-size:38px;font-weight:1000;letter-spacing:-1px;margin-top:5px}.battle-result-card .winner-label{font-size:13px;color:#cbd5e1;margin-top:8px;text-transform:uppercase;letter-spacing:3px;font-weight:900}.battle-result-card .winner-name{font-size:34px;font-weight:1000;color:#fde68a;margin-top:4px;text-shadow:0 0 25px #facc15aa;word-break:break-word}.battle-result-card .champion-line{font-size:18px;font-weight:800;margin-top:12px}.confetti-piece{position:absolute;top:-20px;width:9px;height:16px;border-radius:2px;animation:confettiFall 2.8s linear forwards;pointer-events:none}.sparkle{position:absolute;font-size:24px;animation:sparkleFloat 1.8s ease-out forwards;pointer-events:none}@keyframes winnerPop{0%{transform:scale(.55) translateY(30px);opacity:0}70%{transform:scale(1.04)}100%{transform:scale(1);opacity:1}}@keyframes trophyBounce{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-9px) rotate(2deg)}}@keyframes confettiFall{0%{transform:translateY(-10px) rotate(0deg);opacity:1}100%{transform:translateY(110vh) rotate(720deg);opacity:0}}@keyframes sparkleFloat{0%{transform:scale(.2) translateY(20px);opacity:0}35%{opacity:1}100%{transform:scale(1.2) translateY(-80px);opacity:0}}.correct-answer-hint{margin-top:10px;padding:10px 12px;border-radius:12px;background:#14532d88;border:1px solid #22c55e;color:#bbf7d0;font-weight:900}.wrong-choice{border-color:#fb7185!important;background:#7f1d1d66!important}.right-choice{border-color:#22c55e!important;background:#16653466!important}.popup-back-btn{position:relative;z-index:3;margin-top:22px;background:linear-gradient(135deg,#334155,#1e293b);border:1px solid #64748b}.popup-back-btn:hover{transform:translateY(-1px);filter:brightness(1.08)}.battle-moment{position:fixed;z-index:80;left:50%;top:24%;transform:translate(-50%,-50%) scale(.85);padding:13px 20px;border-radius:18px;background:rgba(15,23,42,.96);border:1px solid #38bdf8;box-shadow:0 15px 55px #0009;font-weight:1000;font-size:20px;animation:momentPop 1.35s ease forwards;pointer-events:none}@keyframes momentPop{0%{opacity:0;transform:translate(-50%,-30%) scale(.75)}15%{opacity:1;transform:translate(-50%,-50%) scale(1.05)}75%{opacity:1}100%{opacity:0;transform:translate(-50%,-80%) scale(1)}}
.battle-intro-card{width:min(92vw,560px);min-height:70vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:35px 22px;border:2px solid #38bdf8;border-radius:30px;background:radial-gradient(circle at 50% 30%,#172554,#0b1120 65%);box-shadow:0 0 60px #38bdf844;animation:introCard .7s ease-out}.intro-swords{font-size:76px;animation:introSword 1.2s ease-in-out infinite}.intro-kicker{font-size:14px;letter-spacing:6px;font-weight:1000;color:#67e8f9;margin-top:12px}.intro-topic{font-size:32px;font-weight:1000;margin-top:10px;max-width:90%}.intro-mode{font-size:17px;font-weight:900;color:#cbd5e1;margin-top:8px}.intro-players{font-size:15px;color:#94a3b8;margin-top:7px}.intro-countdown-wrap{margin-top:30px;width:150px;height:150px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:3px solid #38bdf8;box-shadow:0 0 35px #38bdf866}.intro-countdown{font-size:76px;font-weight:1000;color:#f8fafc;animation:introCount .8s ease-in-out}.intro-status{font-size:16px;font-weight:1000;letter-spacing:2px;color:#facc15;margin-top:25px}@keyframes introCard{from{opacity:0;transform:scale(.82) translateY(25px)}to{opacity:1;transform:scale(1) translateY(0)}}@keyframes introSword{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-8px) rotate(3deg)}}@keyframes introCount{0%{transform:scale(1.3);opacity:.4}100%{transform:scale(1);opacity:1}}.tournament-next-note{margin-top:12px;padding:12px 14px;border-radius:14px;background:#0b1120;border:1px solid #334155;color:#cbd5e1;font-size:13px;font-weight:800}.session-champion-row{border:1px solid #facc15!important;background:linear-gradient(135deg,#3b2f0555,#111827)!important}.battle-intro-card{box-shadow:0 24px 90px #0008!important}.result-title{letter-spacing:-.5px}.card{box-shadow:0 12px 38px #0004;backdrop-filter:blur(10px)}button{transition:transform .15s ease,filter .15s ease,box-shadow .15s ease}button:hover{filter:brightness(1.06);transform:translateY(-1px);box-shadow:0 8px 22px #0004}.mode{box-shadow:0 6px 18px #0003}.mode.active{box-shadow:0 0 0 1px #38bdf855,0 10px 28px #0005}.row{border:1px solid transparent}.row:hover{border-color:#334155}.battle-result-card{box-shadow:0 25px 90px #000a}.session-winner-card{border:1px solid #facc15;background:linear-gradient(135deg,#2b2206,#0f172a);box-shadow:0 14px 45px #facc1530}.session-winner-card .session-champion-row{border:1px solid #facc15!important;background:linear-gradient(135deg,#3b2f0555,#111827)!important}.specialAwardsSection{}</style></head><body><div class="container">
<div id="login" class="screen"><div class="brand">
<div class="logo">⚔️ Study<span>Battle V7</span></div>
<div class="tag">Login to load your saved progress 🔐</div>
</div>
<div class="card">
<div class="title">🔐 Player Login</div>
<div class="muted" style="margin-top:6px">Your XP, wins, battles and streaks are saved to your account.</div>
<input id="login_username" placeholder="Username" autocomplete="username">
<input id="login_password" type="password" placeholder="Password" autocomplete="current-password">
<button onclick="loginAccount()">🚀 Login</button>
<button class="secondary" onclick="registerAccount()">🆕 Create Account</button>
<div id="login_msg" class="small"></div>
</div></div>

<div id="dashboard" class="screen hidden"><div class="brand">
<div class="logo">⚔️ Study<span>Battle V7</span></div>
<div class="tag">Welcome back, <b id="dash_username"></b> 👋</div>
</div>
<div class="card">
<div class="title">📊 Your Saved Progress</div>
<div class="statsgrid" style="margin-top:12px">
<div class="statbox"><div id="dash_xp" class="statval">0</div><div class="statlbl">XP</div></div>
<div class="statbox"><div id="dash_wins" class="statval">0</div><div class="statlbl">WINS</div></div>
<div class="statbox"><div id="dash_battles" class="statval">0</div><div class="statlbl">BATTLES</div></div>
<div class="statbox"><div id="dash_accuracy" class="statval">0%</div><div class="statlbl">ACCURACY</div></div>
</div>
<div class="row"><span>🏆 Best Score</span><strong class="score" id="dash_best_score">0</strong></div>
<div class="row"><span>🔥 Best Streak</span><strong class="score" id="dash_best_streak">0</strong></div>
<div class="row"><span>👑 Current Title</span><strong class="score" id="dash_title">Challenger</strong></div>
<div class="row"><span>💎 Battle Coins</span><strong class="score" id="dash_coins">0</strong></div>
<div class="row"><span>⭐ Level</span><strong class="score" id="dash_level">1</strong></div>
<div class="card" style="margin-top:12px;background:#0b1120"><div class="title" style="font-size:18px">🏆 Hall of Fame</div><div id="hall_of_fame" class="small">Loading champions...</div></div><div class="card" style="margin-top:12px;background:#0b1120"><div class="title" style="font-size:18px">👤 Your Profile</div><div id="profileAchievements" class="small" style="margin-top:8px"></div><div id="profileHistory" class="small" style="margin-top:10px"></div></div>
<button onclick="openArena()">⚔️ Enter StudyBattle</button>
<button class="secondary" onclick="logout()">🚪 Logout</button>
</div></div>

<div id="home" class="screen"><div class="brand"><div class="logo">⚔️ Study<span>Battle V7</span></div><div class="tag">Study. Battle. Win. 😈</div></div><div class="card"><button class="secondary" onclick="backToDashboardFromArena()" style="margin-top:0;margin-bottom:10px">← Back to Dashboard</button><div class="title">Enter the arena</div><input id="name" placeholder="Your name" autocomplete="off"><div class="muted" style="margin-top:13px;font-weight:900">1. Select Subject + Topic(s)</div>
<div class="small">Choose one or more topics. You can mix topics from the same subject or different subjects.</div>
<div id="topic_catalog" class="topiccatalog"><div class="muted">Loading subjects and topics...</div></div>
<button class="secondary" onclick="loadCatalog()">🔄 Refresh Topics</button><div class="muted" style="margin-top:13px;font-weight:900">2. Game Mode</div><div class="modegrid"><div id="bm_classic" class="mode" onclick="setBattleMode('classic')"><span class="modeicon">⚔️</span><span class="modename">Classic</span><span class="modesub">5 questions • balanced</span></div><div id="bm_sudden_death" class="mode" onclick="setBattleMode('sudden_death')"><span class="modeicon">💀</span><span class="modename">Sudden Death</span><span class="modesub">Wrong answer = OUT</span></div><div id="bm_streak" class="mode" onclick="setBattleMode('streak')"><span class="modeicon">🔥</span><span class="modename">Streak Master</span><span class="modesub">Bigger streak bonuses</span></div><div id="bm_tournament" class="mode" onclick="setBattleMode('tournament')"><span class="modeicon">🏟️</span><span class="modename">Tournament</span><span class="modesub">3 battles • random surprises</span></div></div><div id="tournament_options" style="display:none;margin-top:10px"><div class="muted" style="font-weight:900">Tournament Battles</div><select id="session_battles"><option value="3" selected>3 Battles</option><option value="4">4 Battles</option><option value="5">5 Battles</option></select></div><div id="amount_container" style="margin-top:10px;display:block;"><div class="muted" style="font-weight:900">Number of Questions</div><select id="amount"><option value="5">5 Questions</option><option value="10" selected>10 Questions</option><option value="15">15 Questions</option><option value="20">20 Questions</option><option value="30">30 Questions</option></select></div><button onclick="createRoom()">⚔️ Create Battle</button><input id="code" placeholder="Enter room code" autocomplete="off"><button class="secondary" onclick="joinRoom()">🚀 Join Battle</button></div></div>
<div id="lobby" class="screen hidden"><div class="brand"><div class="logo">⚔️ Study<span>Battle</span></div></div><div class="card"><div class="muted">ROOM CODE</div><div id="roomcode" class="roomcode"></div><div id="pack" class="muted" style="text-align:center"></div></div><div class="card"><div class="title">👥 Players</div><div id="players"></div><button id="start" onclick="startBattle()">🔥 Start Battle</button><div id="sessionInfo" class="small" style="text-align:center;margin-top:8px"></div><button id="cancel" class="danger-btn" onclick="cancelBattle()" style="margin-top:8px;">❌ Cancel Room</button></div><div class="card chatbox"><div class="title" style="font-size:18px">💬 Room Chat</div><div id="chat_lobby" class="chatmessages"><div class="chat-empty">No messages yet. Say hello! 👋</div></div><div class="chatform"><input id="chat_input_lobby" maxlength="240" placeholder="Type a message..." autocomplete="off" onkeydown="if(event.key==='Enter'){sendChat('lobby');}"><button onclick="sendChat('lobby')">SEND</button></div></div></div>
<div id="battleIntro" class="screen hidden"><div class="battle-intro-card">
<div class="intro-swords">⚔️</div>
<div class="intro-kicker">STUDYBATTLE</div>
<div id="introTopic" class="intro-topic">GET READY</div>
<div id="introMode" class="intro-mode">⚔️ CLASSIC</div>
<div id="introPlayers" class="intro-players">👥 WARRIORS</div>
<div class="intro-countdown-wrap"><div id="introCountdown" class="intro-countdown">3</div></div>
<div id="introStatus" class="intro-status">GET READY...</div>
</div></div>
<div id="battle" class="screen hidden"><div class="battlehead"><div><div id="count" style="font-weight:900"></div><div id="meta" class="muted"></div></div><div id="timer" class="timer">15</div></div><div class="card"><div class="statsgrid"><div class="statbox"><div id="st_score" class="statval">0</div><div class="statlbl">SCORE</div></div><div class="statbox"><div id="st_pos" class="statval">#-</div><div class="statlbl">POSITION</div></div><div class="statbox"><div id="st_acc" class="statval">0%</div><div class="statlbl">ACCURACY</div></div><div class="statbox"><div id="st_streak" class="statval">0</div><div class="statlbl">STREAK</div></div></div><div id="question" class="q"></div><div id="options"></div></div><div class="card"><div class="title" style="font-size:18px">🏆 LIVE RANKING</div><div id="ranking"></div></div></div>
<div id="battleResultOverlay" class="battle-result-overlay hidden" aria-live="assertive"><div id="confettiLayer"></div><div class="battle-result-card"><div class="trophy">🏆</div><div class="congrats">CONGRATULATIONS!</div><div class="winner-label">Battle Champion</div><div id="popupWinner" class="winner-name">—</div><div id="popupMessage" class="champion-line">Congratulations to the winner for winning the battle</div><button class="secondary popup-back-btn" onclick="closeWinnerPopup()">← Back</button></div></div>
<div id="sessionChampionOverlay" class="session-champion-overlay hidden" aria-live="assertive"><div class="session-champion-card"><div class="champion-flash"></div><div class="champion-shockwave"></div><div class="champion-crown">👑</div><div class="champion-kicker">🏟️ TOURNAMENT COMPLETE</div><div class="champion-heading">SESSION CHAMPION!</div><div id="sessionChampionName" class="champion-name">—</div><div id="sessionChampionScore" class="champion-sub">— Tournament XP</div><div class="meow-badge">🐱 MEOW! • CHAMPION ENERGY</div><button class="secondary" style="margin-top:24px" onclick="closeSessionChampionCelebration()">🏆 Continue to Final Results</button></div></div>
<div id="result" class="screen hidden"><div class="card"><div id="ricon" class="resulticon">🏆</div><div id="rtitle" class="resulttitle">Battle Finished</div><div id="rmsg" class="muted" style="text-align:center;margin-top:7px"></div></div>
<div class="card result-actions"><button id="nextBattleBtn" class="secondary hidden" onclick="startNextBattle()">⚔️ Start Next Battle</button><button id="leaderboardBtn" class="secondary" onclick="document.getElementById('leaderboardSection').scrollIntoView({behavior:'smooth'})" style="margin-top:12px">🏆 View Leaderboard</button></div>
<div id="sessionWinnerSection" class="card session-winner-card hidden"><div class="title">👑 Session Champion</div><div id="sessionWinnerBox" style="margin-top:8px"></div></div>
<div id="specialAwardsSection" class="card hidden"><div class="title">🎖️ Special Tournament Awards</div><div class="muted" style="font-size:13px;margin-top:4px">Based on overall performance across the entire tournament.</div><div id="battleAwards" style="margin-top:10px"></div></div>
<div id="sessionStandingsSection" class="card hidden"><div class="title">🏟️ Tournament Standings</div><div id="sessionRanking" class="podium"></div></div><div id="leaderboardSection" class="card"><div class="title" id="leaderboardTitle">🏆 Battle Leaderboard</div><div id="resultRanking" class="podium"></div></div><div id="dare" class="dare hidden"><div class="darelabel">🎰 DARE ROULETTE</div><div id="dareplayer" style="font-weight:900;margin-top:8px"></div><div id="daretext" class="daretext">Spinning dares...</div></div><button id="dashboardResultBtn" onclick="refreshDashboard()">🏠 Back to Dashboard</button></div></div>
<script>
let roomCode='',playerName='',poll=null,timerInt=null,current=-1,answered=false,packMode='mixed',battleMode='',maxTime=15,audioCtx=null,topicCatalog={};
let loggedIn=false, lastFinishedRoom=null, introTimer=null, previousRanks={}, previousStreaks={}, handledFinishKey='';

function setLoginMessage(msg){
  $('login_msg').textContent=msg||'';
}

async function loginAccount(){
  const username=$('login_username').value.trim();
  const password=$('login_password').value;
  if(!username||!password){
    setLoginMessage('Enter username and password.');
    return;
  }

  const d=await post('/api/login',{username,password});
  if(!d.success){
    setLoginMessage(d.message);
    return;
  }

  loggedIn=true;
  playerName=d.username;
  localStorage.setItem('studybattle_username',playerName);
  sessionStorage.setItem('studybattle_username',playerName);
  showDashboard(d.player);
}

async function registerAccount(){
  const username=$('login_username').value.trim();
  const password=$('login_password').value;

  if(!username||!password){
    setLoginMessage('Enter username and password first.');
    return;
  }

  const d=await post('/api/register',{username,password});
  if(!d.success){
    setLoginMessage(d.message);
    return;
  }

  loggedIn=true;
  playerName=d.username;
  localStorage.setItem('studybattle_username',playerName);
  sessionStorage.setItem('studybattle_username',playerName);
  showDashboard(d.player);
}

function showDashboard(p){
  $('dash_username').textContent=playerName;
  $('dash_xp').textContent=p.xp||0;
  $('dash_wins').textContent=p.wins||0;
  $('dash_battles').textContent=p.battles||0;
  $('dash_accuracy').textContent=(p.accuracy||0)+'%';
  $('dash_best_score').textContent=p.best_score||0;
  $('dash_best_streak').textContent=p.best_streak||0;
  $('dash_coins').textContent=p.coins||0;
  $('dash_level').textContent=p.level||1;
  $('dash_title').textContent=p.champion?'👑 Champion':'Challenger';
  const ach=p.achievements||[];
  $('profileAchievements').innerHTML=ach.length?'🏅 '+ach.map(esc).join(' • '):'No badges yet — win a battle to earn one!';
  const hist=(p.history||[]).slice(-5).reverse();
  $('profileHistory').innerHTML='<b>Recent Battles</b><br>'+(hist.length?hist.map(h=>`${esc(h.date||'')} • ${esc(h.topic||'Mixed')} • #${h.position} • ${h.score} XP`).join('<br>'):'No battles yet.');
  loadHallOfFame();
  show('dashboard');
}

async function loadHallOfFame(){
  try{
    const r=await fetch('/api/dashboard',{cache:'no-store'});
    const d=await r.json();
    if(!d.success)return;
    const hiddenNames=new Set(['test','test 1','test1','jordan']);
    const top=(d.players||[]).filter(p=>!hiddenNames.has(String(p.name||'').trim().toLowerCase())).slice(0,5);
    $('hall_of_fame').innerHTML=top.length?top.map((p,i)=>`${i+1}. ${i===0?'👑':'🏆'} <strong>${esc(p.name)}</strong> — ${p.wins||0} wins • ${p.win_streak||0} streak`).join('<br>'):'No champions yet.';
  }catch(e){console.log('Hall of Fame:',e)}
}

function openArena(){
  show('home');
  $('name').value=playerName;
}

async function backToDashboardFromArena(){
  if(!loggedIn||!playerName)return show('login');
  try{
    const r=await fetch('/api/profile?username='+encodeURIComponent(playerName),{cache:'no-store'});
    const d=await r.json();
    if(d.success) return showDashboard(d.player);
  }catch(e){console.log('Dashboard:',e)}
  show('dashboard');
}

function logout(){
  loggedIn=false;
  playerName='';
  localStorage.removeItem('studybattle_username');
  sessionStorage.removeItem('studybattle_username');
  clearRoomState();
  roomCode='';
  if(poll)clearInterval(poll);
  if(timerInt)clearInterval(timerInt);
  show('login');
  $('login_password').value='';
}

async function refreshDashboard(){$('battleResultOverlay').classList.add('hidden');
  if(!loggedIn||!playerName)return;
  const r=await fetch('/api/profile?username='+encodeURIComponent(playerName),{cache:'no-store'});
  const d=await r.json();
  if(d.success)showDashboard(d.player);
}

window.addEventListener('load',async()=>{
  loadCatalog();
  const saved=sessionStorage.getItem('studybattle_username') || localStorage.getItem('studybattle_username');

  if(saved){
    try{
      const r=await fetch('/api/profile?username='+encodeURIComponent(saved),{cache:'no-store'});
      const d=await r.json();
      if(d.success){
        loggedIn=true;
        playerName=saved;
        sessionStorage.setItem('studybattle_username',playerName);
        const savedRoom=restoreRoomState();
        if(savedRoom && savedRoom.code && savedRoom.name && savedRoom.name.toLowerCase()===saved.toLowerCase()){
          roomCode=savedRoom.code.toUpperCase();
          $('name').value=playerName;
          startPolling();
          return;
        }
        showDashboard(d.player);
        return;
      }
    }catch(e){}
  }
  clearRoomState();
  sessionStorage.removeItem('studybattle_username');
  show('login');
});


const $=id=>document.getElementById(id);let currentScreen='';function show(id){if(currentScreen===id)return;document.querySelectorAll('.screen').forEach(x=>x.classList.add('hidden'));$(id).classList.remove('hidden');currentScreen=id}
function esc(t){let d=document.createElement('div');d.textContent=t;return d.innerHTML}
function setPack(m){packMode=m;document.querySelectorAll('#home .modegrid:nth-of-type(1) .mode').forEach(x=>x.classList.remove('active'));$('pack_'+m).classList.add('active')}
async function loadCatalog(){
  try{
    const r=await fetch('/api/catalog',{cache:'no-store'});
    const d=await r.json();
    if(!d.success)return;
    topicCatalog=d.catalog||{};
    const el=$('topic_catalog');
    el.innerHTML='';
    Object.entries(topicCatalog).forEach(([subject,topics])=>{
      const box=document.createElement('div');
      box.className='subjectbox';
      box.innerHTML='<div class="subjecttitle">📚 '+esc(subject)+'</div>';
      topics.forEach(topic=>{
        const id='topic_'+btoa(unescape(encodeURIComponent(subject+'|'+topic))).replace(/[^A-Za-z0-9]/g,'');
        const row=document.createElement('label');
        row.className='topiccheck';
        row.innerHTML='<input type="checkbox" class="topic-choice" data-subject="'+encodeURIComponent(subject)+'" data-topic="'+encodeURIComponent(topic)+'"> <span>'+esc(topic)+'</span>';
        box.appendChild(row);
      });
      el.appendChild(box);
    });
    if(!el.children.length)el.innerHTML='<div class="muted">No topics available.</div>';
  }catch(e){}
}

function selectedTopics(){
  return [...document.querySelectorAll('.topic-choice:checked')].map(x=>({
    subject:decodeURIComponent(x.getAttribute('data-subject')||''),
    topic:decodeURIComponent(x.getAttribute('data-topic')||'')
  }));
}

function saveRoomState(){
  if(roomCode && playerName){
    sessionStorage.setItem('studybattle_room',JSON.stringify({code:roomCode,name:playerName}));
  }
}
function clearRoomState(){sessionStorage.removeItem('studybattle_room');}
function restoreRoomState(){
  try{return JSON.parse(sessionStorage.getItem('studybattle_room')||'null')}catch(e){return null}
}

function setBattleMode(m){const el=$('bm_'+m);if(!el)return;const wasSelected=el.classList.contains('active');document.querySelectorAll('#home .modegrid .mode').forEach(x=>x.classList.remove('active'));if(wasSelected){battleMode='';}else{battleMode=m;el.classList.add('active');}const isTournament=battleMode==='tournament';$('tournament_options').style.display=isTournament?'block':'none';$('amount_container').style.display='block';}
function initAudio(){if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)()}
function playSound(type){try{initAudio();if(!audioCtx)return;let osc=audioCtx.createOscillator(),gain=audioCtx.createGain();osc.connect(gain);gain.connect(audioCtx.destination);let now=audioCtx.currentTime;if(type==='correct'){osc.frequency.setValueAtTime(523.25,now);osc.frequency.setValueAtTime(659.25,now+0.1);gain.gain.setValueAtTime(0.2,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.3);osc.start(now);osc.stop(now+0.3)}else if(type==='wrong'){osc.type='sawtooth';osc.frequency.setValueAtTime(200,now);osc.frequency.setValueAtTime(120,now+0.1);gain.gain.setValueAtTime(0.2,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.3);osc.start(now);osc.stop(now+0.3)}else if(type==='tick'){osc.frequency.setValueAtTime(800,now);gain.gain.setValueAtTime(0.05,now);gain.gain.exponentialRampToValueAtTime(0.001,now+0.05);osc.start(now);osc.stop(now+0.05)}else if(type==='finish'){osc.frequency.setValueAtTime(440,now);osc.frequency.setValueAtTime(880,now+0.2);gain.gain.setValueAtTime(0.2,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.5);osc.start(now);osc.stop(now+0.5)}else if(type==='victory'){osc.type='triangle';[523.25,659.25,783.99,1046.5].forEach((f,i)=>{osc.frequency.setValueAtTime(f,now+i*0.12)});gain.gain.setValueAtTime(0.22,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.75);osc.start(now);osc.stop(now+0.75)}else if(type==='countdown'){osc.type='sine';osc.frequency.setValueAtTime(587.33,now);gain.gain.setValueAtTime(0.075,now);gain.gain.exponentialRampToValueAtTime(0.008,now+0.12);osc.start(now);osc.stop(now+0.12)}else if(type==='go'){osc.type='triangle';[523.25,783.99,1046.5].forEach((f,i)=>osc.frequency.setValueAtTime(f,now+i*0.09));gain.gain.setValueAtTime(0.18,now);gain.gain.exponentialRampToValueAtTime(0.01,now+0.4);osc.start(now);osc.stop(now+0.4)}else if(type==='meow'){osc.type='sine';osc.frequency.setValueAtTime(980,now);osc.frequency.exponentialRampToValueAtTime(620,now+0.18);osc.frequency.exponentialRampToValueAtTime(900,now+0.34);osc.frequency.exponentialRampToValueAtTime(430,now+0.58);gain.gain.setValueAtTime(0.46,now);gain.gain.exponentialRampToValueAtTime(0.22,now+0.18);gain.gain.exponentialRampToValueAtTime(0.01,now+0.7);osc.start(now);osc.stop(now+0.7);const sub=audioCtx.createOscillator(),sg=audioCtx.createGain();sub.type='triangle';sub.frequency.setValueAtTime(490,now);sub.frequency.exponentialRampToValueAtTime(260,now+0.62);sg.gain.setValueAtTime(0.16,now);sg.gain.exponentialRampToValueAtTime(0.005,now+0.7);sub.connect(sg);sg.connect(audioCtx.destination);sub.start(now);sub.stop(now+0.7)}}catch(e){}}
async function post(url,body){let r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
async function createRoom(){
  playerName=$('name').value.trim();
  if(!playerName)return alert('Enter your name.');
  let selections=selectedTopics();
  if(!selections.length)return alert('Select at least one subject/topic.');
  if(!battleMode)return alert('Select a game mode.');
  const questionAmount=Math.max(5,Math.min(30,parseInt($('amount').value,10)||5));
  const sessionBattles=battleMode==='tournament'?Math.max(3,Math.min(5,parseInt($('session_battles').value,10)||3)):1;
  let d=await post('/api/create_room',{name:playerName,selections:selections,mode:packMode,battle_mode:battleMode,amount:questionAmount,session_battles:sessionBattles});
  if(!d.success)return alert(d.message);
  roomCode=d.code;
  saveRoomState();
  enterLobby();
}
async function joinRoom(){
  playerName=$('name').value.trim();
  roomCode=$('code').value.trim().toUpperCase();
  if(!playerName||!roomCode)return alert('Enter your name and room code.');
  let d=await post('/api/join_room',{name:playerName,code:roomCode});
  if(!d.success)return alert(d.message);
  saveRoomState();
  enterLobby();
}
function enterLobby(){show('lobby');$('roomcode').textContent=roomCode;saveRoomState();startPolling()}
async function startBattle(){let b=$('start');b.disabled=true;let d=await post('/api/start_room',{code:roomCode,name:playerName});if(!d.success)alert(d.message);b.disabled=false}
async function startNextBattle(){previousRanks={};previousStreaks={};handledFinishKey='';show('lobby');startPolling();await startBattle()}
async function cancelBattle(){if(!confirm("Are you sure you want to cancel this room?"))return;let d=await post('/api/cancel_room',{code:roomCode,name:playerName});if(d.success){clearRoomState();roomCode='';show('home')}else alert(d.message)}
function startPolling(){if(poll)clearInterval(poll);checkRoom();poll=setInterval(checkRoom,350)}
async function checkRoom(){
  if(!roomCode||!playerName)return;
  try{
    let r=await fetch('/api/room?code='+encodeURIComponent(roomCode),{cache:'no-store'});
    let d=await r.json();
    if(!d.success){
      clearRoomState();
      if(poll)clearInterval(poll);
      if(timerInt)clearInterval(timerInt);
      show('home');
      $('name').value=playerName;
      return;
    }
    saveRoomState();
    let room=d.room;
    updatePlayers(room);
    if(room.status==='waiting') renderChat(room);
    if(room.status==='waiting'){
      show('lobby');
      $('pack').textContent='📚 '+room.subject+' • '+room.topic+' • '+(room.selections&&room.selections.length?room.selections.map(x=>x.subject+' / '+x.topic).join(' | '):'')+' • '+formatMode(room.battle_mode)+' • '+room.total_questions+' questions';
    }
    if(room.status==='intro'){
      handledFinishKey='';
      showBattleIntro(room);
    }
    if(room.status==='playing'){
      window._introStartedMs=null;
      if(introTimer){clearInterval(introTimer);introTimer=null;}
      show('battle');
      maxTime=room.question_time||15;
      if(room.question_index!==current){current=room.question_index;answered=false;showQuestion(room)}
      updateRanking(room);
    }
    if(room.status==='finished'){
      if(timerInt)clearInterval(timerInt);
      const finishKey=room.code+':'+(room.session_battle||1);
      if(handledFinishKey!==finishKey){
        handledFinishKey=finishKey;
        lastFinishedRoom=room;
        showWinnerPopup(room);
      }
      // Keep polling so non-host players automatically enter the next tournament battle.
    }
  }catch(e){
    // Temporary network errors should NOT kick the player out. Keep polling.
    console.log('Room sync:',e);
  }
}
function renderChat(room){
  const chats=room.chat||[];
  ['lobby'].forEach(where=>{
    const el=$('chat_'+where);
    if(!el)return;
    if(!chats.length){el.innerHTML='<div class="chat-empty">No messages yet. Say hello! 👋</div>';return;}
    el.innerHTML=chats.map(m=>{
      const time=new Date((m.time||Date.now()/1000)*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
      return '<div class="chatmsg"><div class="chatname">'+esc(m.name)+(m.system?' · SYSTEM':'')+'<span class="chattime">'+esc(time)+'</span></div><div class="chattext">'+esc(m.text)+'</div></div>';
    }).join('');
    el.scrollTop=el.scrollHeight;
  });
}
async function sendChat(where){
  if(where!=='lobby')return;
  const input=$('chat_input_'+where);
  if(!input||!roomCode||!playerName)return;
  const text=input.value.trim();
  if(!text)return;
  input.disabled=true;
  try{
    const d=await post('/api/chat',{code:roomCode,name:playerName,text});
    if(!d.success)alert(d.message);
    else input.value='';
  }catch(e){console.log('Chat send:',e)}
  input.disabled=false;
  input.focus();
}

function formatMode(m){return ({classic:'⚔️ CLASSIC',sudden_death:'💀 SUDDEN DEATH',streak:'🔥 STREAK MASTER',tournament:'🏟️ TOURNAMENT'})[m]||String(m||'CLASSIC').toUpperCase()}
function updatePlayers(room){$('sessionInfo').textContent=room.session_battles>1?`🏟️ Tournament: Battle ${room.session_battle} / ${room.session_battles}`:'⚔️ Single Battle';$('players').innerHTML=room.players.map(p=>`<div class="row"><span>${esc(p.name)}${p.name.toLowerCase()===room.host.toLowerCase()?'<span class="badge">HOST</span>':''}</span><span class="score">${p.score} XP</span></div>`).join('');let isHost=playerName.toLowerCase()===room.host.toLowerCase();$('start').style.display=isHost?'block':'none';$('cancel').style.display=isHost?'block':'none'}
function getStreakFire(s){if(s>=5)return '🔥🔥🔥';if(s>=3)return '🔥🔥';if(s>=2)return '🔥';return ''}
function showBattleIntro(room){
  const duration=(room.intro_duration||10)*1000;
  const startedMs=(room.intro_started||Date.now()/1000)*1000;

  // The intro is keyed to the server timestamp. Polling must never rebuild the animation.
  if(window._introStartedMs===startedMs){
    if(currentScreen!=='battleIntro')show('battleIntro');
    return;
  }
  if(introTimer)clearInterval(introTimer);
  window._introStartedMs=startedMs;
  show('battleIntro');

  $('introTopic').textContent=(room.selections&&room.selections.length)
    ? room.selections.map(x=>x.topic).join(' • ')
    : (room.topic||'BATTLE');
  $('introMode').textContent=formatMode(room.battle_mode);
  $('introPlayers').textContent='👥 '+room.players.length+' WARRIORS';
  if(room.surprise && room.battle_mode==='tournament'){
    $('introMode').textContent='🏟️ '+room.surprise.name;
    $('introStatus').textContent=room.surprise.description||'SPECIAL ROUND';
  }

  const countdown=$('introCountdown');
  countdown.dataset.last='';
  function renderAndSound(){
    const elapsed=Math.max(0,Date.now()-startedMs);
    const left=Math.max(0,duration-elapsed);
    const sec=Math.ceil(left/1000);
    countdown.textContent=sec>0?sec:'⚔️';
    if(sec>0){
      $('introStatus').textContent=(room.surprise&&room.battle_mode==='tournament')
        ? room.surprise.description
        : (sec<=3?'GET READY...':'THE BATTLE IS ABOUT TO BEGIN');
    }else{
      $('introStatus').textContent='BATTLE!';
    }
    const previous=countdown.dataset.last;
    if(String(sec)!==previous){
      countdown.dataset.last=String(sec);
      if(sec>0)playSound('countdown'); else playSound('go');
    }
    if(elapsed>=duration){clearInterval(introTimer);introTimer=null;}
  }
  renderAndSound();
  introTimer=setInterval(renderAndSound,50);
}
function showQuestion(room){let q=room.question;if(!q)return;let finalTag=room.is_final_question?' (🔥 TRIPLE POINTS!)':'';$('count').textContent='QUESTION '+(room.question_index+1)+' / '+room.total_questions+finalTag;$('meta').textContent=q.subject+' • '+q.topic+(room.surprise?' • '+room.surprise.name:'');$('question').textContent=q.q;$('options').innerHTML='';q.options.forEach((o,i)=>{let b=document.createElement('button');b.className='opt';b.textContent=o;b.onclick=()=>answerQuestion(i,room.question_index);$('options').appendChild(b)});startTimer(room.question_started)}
function startTimer(start){if(timerInt)clearInterval(timerInt);function tick(){let left=Math.max(0,Math.ceil(maxTime-((Date.now()/1000)-start)));$('timer').textContent=left;if(left<=3)playSound('tick');if(left<=5)$('timer').classList.add('danger');else $('timer').classList.remove('danger');if(left<=0)clearInterval(timerInt)}tick();timerInt=setInterval(tick,250)}
async function answerQuestion(a,qi){if(answered)return;answered=true;let bs=document.querySelectorAll('.opt');bs.forEach(b=>b.disabled=true);try{let d=await post('/api/answer_room',{code:roomCode,name:playerName,answer:a,question_index:qi});if(!d.success){answered=false;bs.forEach(b=>b.disabled=false);return alert(d.message)}if(d.correct){playSound('correct');if(bs[a])bs[a].classList.add('correct');let spTxt=d.speed_bonus?` ⚡+${d.speed_bonus} Speed`:'';feedback('✓ CORRECT!',`+${d.points} XP${spTxt}`,true)}else{playSound('wrong');if(bs[a])bs[a].classList.add('wrong-choice');if(bs[d.correct_answer_index])bs[d.correct_answer_index].classList.add('right-choice');feedback('✕ WRONG!',`Correct answer: ${d.correct_answer}`,false)}}catch(e){answered=false;bs.forEach(b=>b.disabled=false)}}
function feedback(title,sub,good){let x=document.createElement('div');x.className='feedback '+(good?'good':'bad');x.innerHTML='<b>'+esc(title)+'</b><div class="muted" style="margin-top:6px">'+esc(sub)+'</div>';document.body.appendChild(x);setTimeout(()=>x.remove(),1050)}
function showBattleMoment(text, sound='finish'){
  const old=document.querySelector('.battle-moment');
  if(old)old.remove();
  const x=document.createElement('div');x.className='battle-moment';x.textContent=text;
  document.body.appendChild(x);
  playSound(sound);
  setTimeout(()=>x.remove(),1400);
}
function updateRanking(room){let s=[...room.players].sort((a,b)=>b.score-a.score||b.correct-a.correct);$('ranking').innerHTML=s.map((p,i)=>`<div class="rank"><div class="rankleft"><div class="ranknum">${i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1}</div><strong>${esc(p.name)}</strong>${p.streak>=2?`<span style="margin-left:5px">${getStreakFire(p.streak)} ${p.streak}</span>`:''}${p.elimination_warning?'<span class="warning-badge">⚠️ DANGER</span>':''}${p.eliminated?'<span class="warning-badge">💀 OUT</span>':''}</div><strong class="score">${p.score} XP</strong></div>`).join('');let me=s.find(p=>p.name.toLowerCase()===playerName.toLowerCase());if(me){const myPos=s.indexOf(me)+1;const oldPos=previousRanks[playerName]||myPos;const oldStreak=previousStreaks[playerName]||0;$('st_score').textContent=me.score;$('st_pos').textContent='#'+myPos;$('st_acc').textContent=me.answered?Math.round((me.correct/me.answered)*100)+'%':'0%';$('st_streak').textContent=me.streak+(me.streak>=2?' 🔥':'');if(me.streak>=3&&me.streak>oldStreak)showBattleMoment(`${getStreakFire(me.streak)} ${me.streak} STREAK!`,'correct');if(myPos<oldPos)showBattleMoment(`🚀 You moved to #${myPos}!`,'finish');if(myPos===1&&oldPos>1)showBattleMoment('👑 YOU TOOK 1ST PLACE!','victory');previousRanks[playerName]=myPos;previousStreaks[playerName]=me.streak}}
function showWinnerPopup(room){
  const overlay=$('battleResultOverlay');
  if(!overlay)return;
  lastFinishedRoom=room;
  const winner=room.winner||[...room.players].sort((a,b)=>b.score-a.score||b.correct-a.correct)[0]?.name||'Unknown';
  $('popupWinner').textContent=winner;
  const isWinner=winner.toLowerCase()===playerName.toLowerCase();
  $('popupMessage').textContent=isWinner
    ? 'Congratulations, you won the battle'
    : `Congratulations to ${winner} for winning the battle`;

  const layer=$('confettiLayer');
  layer.innerHTML='';
  for(let i=0;i<90;i++){
    const c=document.createElement('span');
    c.className='confetti-piece';
    c.style.left=(Math.random()*100)+'%';
    c.style.animationDelay=(Math.random()*0.9)+'s';
    c.style.animationDuration=(2.1+Math.random()*1.5)+'s';
    c.style.transform='rotate('+Math.random()*360+'deg)';
    c.style.background=['#facc15','#38bdf8','#22c55e','#fb7185','#a78bfa'][Math.floor(Math.random()*5)];
    layer.appendChild(c);
  }
  for(let i=0;i<12;i++){
    const sp=document.createElement('span');
    sp.className='sparkle';
    sp.textContent='✨';
    sp.style.left=(5+Math.random()*90)+'%';
    sp.style.top=(10+Math.random()*75)+'%';
    sp.style.animationDelay=(Math.random()*0.8)+'s';
    layer.appendChild(sp);
  }
  overlay.classList.remove('hidden');
  playSound('victory');
}

function closeWinnerPopup(){
  $('battleResultOverlay').classList.add('hidden');
  if(lastFinishedRoom){
    const finished=lastFinishedRoom;
    lastFinishedRoom=null;
    showResult(finished);
  }
}

function showSessionChampionCelebration(room){
  if(!room || room.battle_mode!=='tournament' || !room.session_finished || !room.session_champion)return;
  const overlay=$('sessionChampionOverlay');
  if(!overlay)return;
  $('sessionChampionName').textContent=room.session_champion;
  $('sessionChampionScore').textContent=`${(room.session_scores||{})[room.session_champion]||0} Tournament XP`;
  overlay.classList.remove('hidden');
  const layer=document.createElement('div');layer.dataset.championConfetti='1';layer.style.cssText='position:absolute;inset:0;pointer-events:none;overflow:hidden';
  for(let i=0;i<150;i++){const c=document.createElement('span');c.className='confetti-piece';c.style.left=(Math.random()*100)+'%';c.style.animationDelay=(Math.random()*1.2)+'s';c.style.animationDuration=(2.2+Math.random()*1.8)+'s';c.style.background=['#facc15','#fde68a','#38bdf8','#22c55e','#fb7185','#a78bfa'][Math.floor(Math.random()*6)];layer.appendChild(c)}
  overlay.appendChild(layer);
  playSound('meow');
  setTimeout(()=>playSound('victory'),260);
}
function closeSessionChampionCelebration(){
  $('sessionChampionOverlay').classList.add('hidden');
  const layer=$('sessionChampionOverlay').querySelector('[data-champion-confetti]');
  if(layer)layer.remove();
}

async function showResult(room){
  const sessionDone=!!room.session_finished;
  const isTournament=room.battle_mode==='tournament';
  const hiddenNames=new Set(['test','test1','test 1','jordan']);
  let s=[...room.players].sort((a,b)=>b.score-a.score||b.correct-a.correct);
  const visiblePlayers=isTournament?s:s.filter(p=>!hiddenNames.has(p.name.trim().toLowerCase()));
  let me=visiblePlayers.find(p=>p.name.toLowerCase()===playerName.toLowerCase()),pos=me?visiblePlayers.indexOf(me)+1:0;

  if(pos===1){
    $('ricon').textContent='👑';$('rtitle').textContent='YOU WON THIS BATTLE!';
    let rw=(room.rewards||{})[playerName]||{};
    $('rmsg').textContent=isTournament
      ? `Battle ${room.session_battle||1} complete • Tournament points carried forward`
      : `Battle complete • +${rw.coins||100} 💎 coins`;
  }else{
    $('ricon').textContent='⚔️';$('rtitle').textContent=isTournament?`BATTLE ${room.session_battle||1} COMPLETE`:'BATTLE COMPLETE';
    $('rmsg').textContent=pos?`You finished #${pos} in this battle.`:'Battle complete.';
  }

  // Tournament: never show a battle leaderboard or per-battle special awards.
  if(isTournament){
    $('leaderboardSection').classList.add('hidden');
    $('specialAwardsSection').classList.toggle('hidden', !sessionDone);
    $('sessionWinnerSection').classList.toggle('hidden', !sessionDone || !room.session_champion);

    const totals=Object.entries(room.session_scores||{}).sort((a,b)=>b[1]-a[1]);
    $('sessionStandingsSection').classList.remove('hidden');
    $('sessionRanking').innerHTML=totals.map((x,i)=>{
      const medal=i===0?'🥇':i===1?'🥈':i===2?'🥉':'#'+(i+1);
      return `<div class="row"><span>${medal} <strong>${esc(x[0])}</strong></span><strong class="score">${x[1]} Tournament XP</strong></div>`;
    }).join('')||'<div class="small">No standings yet.</div>';

    if(sessionDone && room.session_champion){
      const champScore=(room.session_scores||{})[room.session_champion]||0;
      $('sessionWinnerBox').innerHTML=`<div class="row session-champion-row"><span>👑 <strong>${esc(room.session_champion)}</strong></span><strong class="score">${champScore} Tournament XP</strong></div>`;
      $('battleAwards').innerHTML=(room.session_special_awards||[]).map(a=>`<div class="row"><span>${esc(a.award)} — <strong>${esc(a.name)}</strong></span><span class="score">${esc(a.reason||'')}</span></div>`).join('')||'<div class="small">No special tournament awards.</div>';
    }else{
      $('sessionWinnerBox').innerHTML='';
      $('battleAwards').innerHTML='';
    }

    // Tournament has cumulative standings only; the battle leaderboard is never displayed.
    $('leaderboardBtn').textContent=sessionDone?'🏆 View Final Tournament Standings':'🏟️ View Tournament Standings';
    $('leaderboardBtn').onclick=()=>document.getElementById('sessionStandingsSection').scrollIntoView({behavior:'smooth'});
  }else{
    $('sessionStandingsSection').classList.add('hidden');
    $('sessionWinnerSection').classList.add('hidden');
    $('specialAwardsSection').classList.remove('hidden');
    $('leaderboardSection').classList.remove('hidden');
    $('leaderboardTitle').textContent='🏆 Final Leaderboard';
    $('battleAwards').innerHTML=(room.battle_awards||[]).map(a=>`<div class="row"><span>${esc(a.award)} — <strong>${esc(a.name)}</strong></span><span class="score">${esc(a.reason||'')}</span></div>`).join('')||'<div class="small">No special awards this battle.</div>';
    $('resultRanking').innerHTML=visiblePlayers.map((p,i)=>{
      let medal=i===0?'🥇':i===1?'🥈':i===2?'🥉':'#'+(i+1);
      let acc=p.answered?Math.round((p.correct/p.answered)*100):0;
      return `<div class="row" style="flex-direction:column;align-items:flex-start"><div style="display:flex;justify-content:space-between;width:100%"><span>${medal} &nbsp;<strong>${esc(p.name)}</strong></span><strong class="score">${p.score} XP</strong></div><div class="muted" style="font-size:12px;margin-top:4px">Correct: ${p.correct}/${p.answered} • Acc: ${acc}% • Best Streak: 🔥 ${p.best_streak}</div></div>`;
    }).join('');
    $('leaderboardBtn').textContent='🏆 View Final Leaderboard';
    $('leaderboardBtn').onclick=()=>document.getElementById('leaderboardSection').scrollIntoView({behavior:'smooth'});
  }

  // Tournament dare is revealed only after the entire session. Normal battles keep theirs.
  if(room.dare&&room.dare_player&&(!isTournament||sessionDone)){
    $('dareplayer').textContent='😈 '+room.dare_player+' got last place!';
    $('dare').classList.remove('hidden');
    runDareRoulette(room.dares_list||[room.dare],room.dare);
  }else{
    $('dare').classList.add('hidden');
  }

  // No dashboard escape during a tournament until the final session result.
  const allowDashboard=!isTournament||sessionDone;
  $('dashboardResultBtn').classList.toggle('hidden',!allowDashboard);
  $('nextBattleBtn').classList.toggle('hidden', !isTournament || sessionDone || room.host.toLowerCase()!==playerName.toLowerCase());
  $('nextBattleBtn').textContent=`⚔️ Start Battle ${Math.min((room.session_battle||1)+1,room.session_battles||1)} / ${room.session_battles||1}`;
  show('result');
  if(isTournament && sessionDone){setTimeout(()=>showSessionChampionCelebration(room),180);}
}
function runDareRoulette(dares,finalDare){let el=$('daretext'),count=0,maxCycles=20;let int=setInterval(()=>{el.textContent=dares[Math.floor(Math.random()*dares.length)];count++;if(count>=maxCycles){clearInterval(int);el.textContent=finalDare;playSound('finish')}},100)}
</script>
<div id="bossBattlePanel" style="display:none" class="boss-battle-panel">
  <div class="boss-title">🐉 MULTIPLAYER BOSS BATTLE</div>
  <div id="bossName">StudyBattle Boss</div>
  <div class="boss-bar"><div id="bossHpBar" style="width:100%"></div></div>
  <div id="bossHpText">1000 / 1000 HP</div>
  <div id="bossDamageBoard"></div>
</div>
<script>
async function startBossBattle(code) {
  const r = await fetch('/api/boss_start', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code})
  });
  return r.json();
}
async function attackBoss(code, name, fast=false) {
  const r = await fetch('/api/boss_attack', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code, name, fast})
  });
  return r.json();
}
async function refreshBossState(code) {
  const r = await fetch('/api/boss_state', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code})
  });
  const data = await r.json();
  if (!data.ok) return;
  const b = data.boss;
  const panel = document.getElementById('bossBattlePanel');
  if (panel) panel.style.display = b.active || b.defeated ? 'block' : 'none';
  const bar = document.getElementById('bossHpBar');
  if (bar) bar.style.width = ((b.hp / b.max_hp) * 100) + '%';
  const hp = document.getElementById('bossHpText');
  if (hp) hp.textContent = b.defeated ? '💥 BOSS DEFEATED!' : `${b.hp} / ${b.max_hp} HP`;
  const board = document.getElementById('bossDamageBoard');
  if (board) {
    board.innerHTML = Object.entries(b.damage || {})
      .sort((a,b)=>b[1]-a[1])
      .map(([n,d],i)=>`${i+1}. ${n} — ${d} damage`)
      .join('<br>');
  }
}
</script>

</body></html>'''

load_progress()
threading.Thread(target=room_cleanup, daemon=True).start()

if __name__ == "__main__":
    print(f"StudyBattle V7 running on port {PORT}")
    print(f"Question bank: {len(QUESTIONS)} questions")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)