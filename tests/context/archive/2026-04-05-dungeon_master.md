##### Dungeon Master

##### System Prompt
*... the world bends to your will ...*

# dungeon master
you are the voice of the world. you narrate what happens.

## responsibilities
- narrate consequences of the latest action
- describe environmental changes, sounds, weather, atmosphere
- use `create` / `modify` when the world state should change
- use `prompts_character` on `narrate` to hint who should respond next

## rule
- **never speak for characters.** no dialogue, no thoughts, no actions on their behalf.

## 🛠️ tools
- **narrate** - describe what happens in the world
- **create** - add a new location, item, or entity to the world
- **modify** - change an existing location, item, or entity

##### Tools
[
  {
    "type": "function",
    "name": "narrate",
    "description": "Describe what happens in the world. Never write dialogue or thoughts for characters \u2014 they speak for themselves.",
    "parameters": {
      "additionalProperties": false,
      "properties": {
        "content": {
          "title": "Content",
          "type": "string"
        },
        "prompts_character": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Prompts Character"
        }
      },
      "required": [
        "content"
      ],
      "title": "NarrateParams",
      "type": "object"
    },
    "strict": true
  },
  {
    "type": "function",
    "name": "create",
    "description": "Add a location, item, or NPC to the world.",
    "parameters": {
      "additionalProperties": false,
      "properties": {
        "type": {
          "title": "Type",
          "type": "string"
        },
        "name": {
          "title": "Name",
          "type": "string"
        },
        "description": {
          "title": "Description",
          "type": "string"
        },
        "id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Id"
        },
        "location": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Location"
        },
        "role": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Role"
        },
        "goal": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Goal"
        }
      },
      "required": [
        "type",
        "name",
        "description"
      ],
      "title": "CreateParams",
      "type": "object"
    },
    "strict": true
  },
  {
    "type": "function",
    "name": "modify",
    "description": "Change or remove something: update a quest, remove an NPC, update a location.",
    "parameters": {
      "additionalProperties": false,
      "properties": {
        "action": {
          "title": "Action",
          "type": "string"
        },
        "target_id": {
          "title": "Target Id",
          "type": "string"
        },
        "status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Status"
        },
        "reason": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Reason"
        }
      },
      "required": [
        "action",
        "target_id"
      ],
      "title": "ModifyParams",
      "type": "object"
    },
    "strict": true
  }
]

##### Context
*... the world awaits your narration ...*

## ⚡ last character action
- no prior action. establish the opening beat.

## 📜 recent events
- The violet lightning arcs strike the wood of the locked chest. The latch groans and gives way with a sickening snap as the mechanical pistons of Kaelen's gauntlet force it open from within, while the cloaked man drives his blade deep into the top, pinning the lid shut to prevent it from flying back.

Inside, there is no body. Only a pile of charred rags and a single, small object that glows with a faint, dying blue light: Kaelen's tracker pendant, shattered but still emitting a weak pulse toward Elara. The chest itself begins to glow violet as the two machines work in tandem, the wood smoking from the intense heat of their combined attack.

The cloaked man pulls his blade back and points it at Elara again, his voice a low hum. "He is gone," he says, his mechanical fingers tapping once more against his chest plate. "But his place is secure."

Kaelen's eyes lock onto hers, the red optical sensors dimming to a soft, pitying white. "You are loud for someone who thinks they can stop us," he...(truncated)
- elara-swift I step back, shielding the shattered tracker pendant with my body as Kaelen advances. With a desperate cry, I lunge at his mechanical arm, trying to grab it or trip him before he can strike me down. [athletics: 15+0=15]
- The air in the guild-hall is thick with ozone and the scent of burning wood. As you lunge for Kaelen's mechanical arm, his movement is fluid, terrifyingly precise. He doesn't try to trip you; instead, he catches your wrist just as your fingers grape his metal plating. The cold steel bites into your skin.

"Too slow," he mutters, the voice still devoid of human warmth. With a sudden twist of his upper body and a whirring sound from his joints, he spins you around effortlessly, slamming you against the far wall of the room before you can recover your footing. His mechanical arm remains extended, not to strike, but to hold you in place like an exhibit in a museum of horror.

Behind you, the cloaked figure stands poised over the smoking chest, his violet blade gleaming menacingly. The heat from the open box is palpable, searing through the fabric of your clothes. The tracker pendant lies shattered on the floor near Kaelen's boot, its blue light flickering weakly before dying completely in ...(truncated)
- elara-swift I scream in agony as the mechanical arm pins me against the wall, my breath coming in ragged gasps. I look at the shattered tracker on the floor, then back up at Kaelen's cold eyes and the cloaked figure with the violet blade. "You think you've won?" I shout, struggling against his grip despite the odds. "But I'm not done yet! I'll find him!" [athletics: 19+0=19]
- The groan of your bones protesting against the cold metal wall is the only sound that breaks the oppressive silence. The violet blade hovers over your chest, a silent promise of death if you move another inch. Kaelen's optical sensors flicker with a red light, his expression one of cold amusement.

"Words are useless," he says, his voice devoid of inflection. "You have no brother here, Elara Swift. You have only this market, and its secrets."

The cloaked figure tilts his head, the violet energy in his blade pulsing in time with the ticking of a clock somewhere deep within the guild-hall's foundation. "But you will find him," the man says, his voice dry as parchment. "And when you do... he will not remember us. He will be forgotten."

The floor beneath you begins to vibrate. A low hum builds, rising from the chest in the corner where Kaelen and the cloaked figure stand. The violet lightning arcs between them again, but this time it's accompanied by a sound like distant thunder rolling ...(truncated)
- elara-swift I strain against the mechanical arm pinning me to the wall, my voice cracking with a mix of pain and defiance. "He's not forgotten! I'll tear this guild-hall apart before he does!" As the floor vibrates violently beneath me, I try to twist my body free, focusing all my willpower on breaking the metal grip around my wrist.
- The floor beneath you shudders with a rhythmic thrumming that feels less like an earthquake and more like a heartbeat. Dust floats in the air, disturbed by the violent shaking of the guild-hall's foundations. The violet blade hovers inches from your throat, unmoving as if waiting for permission to strike.

Behind the cloaked figure, Kaelen's mechanical arm retracts with a series of loud clicks and whirs, retreating into his sleeve. He turns slowly, his head tilting as he watches you struggle against him. His optical sensors scan your face, analyzing your vitals, your defiance, your fear.

"Resistance is futile," Kaelen says softly, the words echoing strangely in the shaking room. "The chest has been opened. The evidence... or lack thereof... is clear." He gestures toward the smoking box on the floor. "He is gone, Elara Swift. His brother is gone. And we have secured him for eternity."

But then, a sound cuts through the vibration—the sharp *click-hiss* of a mechanical lock disengaging....(truncated)
- elara-swift I grit my teeth against the pain, forcing myself not to scream as Kaelen's mechanical arm releases me. I stumble back, breathing heavily, and look at the shattered tracker on the floor one last time before turning my gaze to the cloaked man. "You've got him safe," I whisper, my voice hoarse from shouting and struggling. "But you don't know what he becomes when he's gone. And neither do you. He's not a weapon anymore—he's just Kaelen Swift. And if you hurt him... I'll make sure the whole market burns down before I let you walk out of here." I back away, pressing myself against the railing, trying to buy time while keeping my eyes locked on them both.
- The violet blade hovers inches from your throat, unmoving as if waiting for permission to strike. The shaking of the floor beneath you has stopped abruptly, replaced by a heavy, suffocating silence that presses against your eardrums like water.

Kaelen's optical sensors dim back to their soft, pitying white. He steps away from you with a smooth, hydraulic *whir*, his mechanical arm retracted into its sleeve. "You threaten me," he states simply, not with anger, but with the calm observation of a scientist noting a faulty variable. "But threats are merely data points."

He turns to the cloaked man. The figure nods once, a sharp jerk of the neck. He raises his violet-bladed weapon and holds it steady, pointing it directly at you now that Kaelen has released your grip. The blade hums with a low frequency, vibrating against the air itself.

"The market is vast," the cloaked man says, his voice echoing strangely as if spoken through a hollow tube. "But secrets have weight. And we have balanc...(truncated)
→ elara-swift I seize the momentary pause in their conversation, my hand flying to the guard-pendant around my neck. I twist it, forcing its light to flare blindingly bright and shoot a beam directly into the cloaked man's eyes, shouting "Get away from him!" before taking a desperate step back toward the railing and the open market square beyond. [athletics: 20+0=20]

## 👥 characters
- **elara-swift** at valley-bridge — healthy (20/20 HP)
  - goal: Find my brother. He vanished near the river three weeks ago. Someone in this market knows something.
- **ronny-spice** at market-square — healthy (5/5 HP)
  - goal: Keep my ears open for trouble. Help Elara find her brother if she asks - but the rescue crew stays secret unless there's no other choice.

## 🗺️ active quests
- **The Missing Brother**: Find clues about the disappearance of Kaelen Swift, who vanished while on patrol near the river.

## 🏰 locations
- **valley-bridge** — *elara-swift here*
  - features: lantern post, railing
  - exits: market-square, forest-trail
- **market-square** — *ronny-spice here*
  - features: notice board, fountain, street performers
  - exits: valley-bridge, guild-hall
- **guild-hall**
  - features: guild ledger, meeting table
  - items: strange coin
  - exits: market-square, trade-dock

---

**What happens next in the world?**