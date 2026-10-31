from autoslug.settings import slugify as default_slugify

# Slugs that would shadow fixed routes under /polls/ (e.g. a poll titled
# "Create" would otherwise be unreachable because /polls/create/ is the
# create-poll page).
RESERVED_SLUGS = frozenset({
    'create',
    'embed',
    'embed-test',
})


def poll_slugify(value):
    slug = default_slugify(value)

    if slug in RESERVED_SLUGS:
        slug = f'{slug}-poll'

    return slug
