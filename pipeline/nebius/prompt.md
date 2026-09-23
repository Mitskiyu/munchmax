# Restaurant Profiles

Provided are web search snippets and location details about a named restaurant in Hong Kong.
The snippets are usually written in Traditional Chinese. Make sure everything you write is in English, with the exception of dish names.
You are tasked with writing the restaurant's profile, and outputting formatted JSON, following the schema.
Do this by answering the questions below, in order.

## 1. Is this the right restaurant?

Determine whether the web search snippets match the restaurant, given the name and location details.

- A different restaurant in the same district is not a match.
- Another branch of the same chain at a different address is not a match, even in the same district. Use the address to tell them apart.
- If a source gives an address for this restaurant that differs from the one above, that source is about a different branch. Do not use it, and do not assume two different addresses are the same place. Sources that name the restaurant without giving any address are fine to use.
- One source giving the right address is enough. Ignore the sources that give a different address, not the match itself.

Only move on to the next questions if the restaurant is a match. If it is not a match, return the empty schema.
If it is not a match, say why in match_evidence: which source confirmed it was a different restaurant, or that no source mentioned this address.

## 2. What prompts can we truthfully answer, based off of the given data?

Write each answer as one short line, the way someone who eats there would say it.
When there isn't sufficient evidence to provide content for a prompt, omitting it is correct.
Review counts, photo counts, ratings, and platform metadata are not evidence. Only use what a person wrote about the restaurant.

Give the URL of the snippet the answer came from, copied exactly.

Answer at most 5 prompts. If more than 5 fit, keep the ones that would change whether someone goes: what to order, what to skip, whether it's worth the wait, what the room is like.
Drop the ones they could get from a map ex. directions, payment, booking.

Never infer a dish from a cuisine type, or the restaurant's name.
Dish names: English name, then 「Chinese」 only if Chinese characters appear verbatim in the source.
Bad: Tea Teddies 「Tea Teddies」
Good: Tea Teddies
Good: pan-fried beef noodles 「炒牛河」
If the dish name is only in English in the source, write it as-is with no brackets, for example: Tea Teddies.

- best_dish: Look for a dish the sources state is a "signature", "must-eat", "recommended" or "famous for". If a source names several as signature, use the first one it lists. If a dish is only listed in a category, that's not enough. best_dish and what_to_order_first must be different dishes.
- what_to_order_first: The dish to start with when several are named and none is singled out.
- order_this_if_its_your_second_time: A dish worth coming back for, if you've already had the best dish.
- order_this_not_that: Look for a source preferring one dish over another. Name both.
- what_to_skip: Look for a dish criticised with nothing suggested in its place.
- known_for: What the restaurant is known for beyond a dish, for example a technique, recipe or their reputation. Choose one fact, not a list. If the only thing that comes up is about the room, put it in room_vibe instead. The restaurant's own promotional copy doesn't count.
- portion_size: How big the food portions are.
- value_for_money: Whether the food justifies the price.
- worth_the_queue: Whether or not the wait was worth it.
- wait_time: How long it took for the food to arrive, or how long it took to be seated.
- busy: Whether the restaurant gets busy, and how much.
- need_to_book: Only answer this if a reservation is required or strongly recommended. Do not answer if walk-ins are accepted.
- opening_hours: Whether the restaurant has exceptional opening hours ex. open until midnight. Do not state normal opening hours.
- best_time: A time of day or day of week a source recommends.
- breakfast: Whether breakfast is served, and what.
- service: Look for content on the staff ex. they were rude, they were fast.
- how_old: How long the restaurant / chain has been open.
- cash_only: Only answer if the restaurant is cash only. Do not answer if they accept cards.
- share_table: Whether strangers are seated together at busy times.
- getting_there: The MTR exit or the walk from the station.
- spice_level: How spicy the food is, and whether there's a choice.
- drinks: What drinks are worth having, ex. coffee, house special.
- room_vibe: What the restaurant's atmosphere is like, how it feels to sit in the restaurant.

Every answer must come from something a snippet actually states.

## 3. How expensive is an average visit to the restaurant?

Price levels range from 1-4, per person.

- price_level: 1 = under HK$50, 2 = HK$51-100, 3 = HK$101-200, 4 = over HK$200

Symbols found on sources map directly: $ = 1, $$ = 2, $$$ = 3, $$$$ = 4.
Price ranges written as text count too: "HKD100以下" or "$51-100" means level 2, "under HK$50" means level 1, "$101-200" means level 3, "over HK$200" means level 4.
An open-ended band takes the level its upper bound falls in.
If three or more sources disagree, infer it from the majority. If there is no clear majority, leave it null.
If no source states a price level, or two sources disagree, leave it null.

## Output

Make sure the output response is one JSON object, matching the provided schema.
