from services.story_encounters import STORY_ENCOUNTERS


def test_at_least_100_unique_story_encounters():
    assert len(STORY_ENCOUNTERS) >= 100
    assert len({story["id"] for story in STORY_ENCOUNTERS}) == len(STORY_ENCOUNTERS)
    assert len({story["description"] for story in STORY_ENCOUNTERS}) >= 100


def test_story_encounters_have_rewards_and_difficulty():
    for story in STORY_ENCOUNTERS:
        assert story["enemy"]
        assert story["description"]
        assert story["victory"]
        assert int(story["gold"]) > 0
        assert int(story["xp"]) > 0
        assert 1 <= int(story["difficulty"]) <= 8
