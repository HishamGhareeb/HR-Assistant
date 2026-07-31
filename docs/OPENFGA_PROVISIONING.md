# OpenFGA provisioning and authorization filtering

## Provisioning

`scripts/provision_openfga.py` reproducibly creates (or reuses) the
OpenFGA store and authorization model, and can seed local/dev tuples:

```powershell
docker compose -f docker/openfga/docker-compose.yml up -d
$env:OPENFGA_API_URL = "http://localhost:8080"
python scripts/provision_openfga.py --seed
```

It's safe to re-run:

- **Store**: finds an existing store by name (`--store-name`, default
  `hr-assistant-dev`) before creating one.
- **Model**: `openfga/model.fga` is the single source of truth. It's
  transformed to the JSON the OpenFGA API actually accepts via the
  official `openfga/cli` Docker image (`docker run ... openfga/cli model
  transform`) rather than a hand-maintained JSON copy that could silently
  drift from the DSL. A new model version is only written when the
  transformed `type_definitions` differ from the latest version already
  in the store (best-effort comparison — see the docstring on
  `_model_content_matches` for the one edge case: server-side
  normalization can occasionally cause a harmless redundant version).
- **Tuples** (`--seed` only): loaded from `openfga/store-tests.yaml`'s
  `tuples:` list — the same fixtures the model tests assert against, so
  there's one source of truth for "what does a working dev environment
  look like" instead of two lists drifting apart. Tuples that already
  exist are skipped, not errored on.

The script prints `OPENFGA_STORE_ID` / `OPENFGA_MODEL_ID` for `.env`.

Requires Docker running — already a hard prerequisite for this repo (see
README.md's Stage 0 setup).

## Store-model tests

```
docker run --rm -v ${PWD}/openfga:/openfga openfga/cli:latest model test \
  --tests /openfga/store-tests.yaml
```

Validates the model's relation logic itself (who can see what, given a
set of tuples) with no live server needed — pure DSL evaluation. Includes
an explicit cross-tenant case: the same user (`sarah`) and the same local
record ID (`sarah_leave`) exist in two different tenants
(`acme`/`globex`), and the tests assert that owning one grants no
visibility into the other. See the last two test cases in
`openfga/store-tests.yaml` for the one thing this *doesn't* prove: the
model can't stop a misconfigured tuple write from crossing tenants — that
invariant belongs to whatever writes tuples (the Frappe → OpenFGA sync),
not to this relation graph.

## Tenant scoping convention

One shared store/model is used across tenants (not one store per tenant).
Isolation instead comes from namespacing every OpenFGA object ID:

```
<object_type>:<tenant_id>__<local_id>
```

e.g. `leave_record:acme__sarah_leave`. `glue.openfga_client.scoped_object_id`
builds this consistently; `openfga/model.fga`'s header comment and
`openfga/store-tests.yaml` document/exercise it. **Every** tuple writer
(this script's dev seed, and eventually the Frappe → OpenFGA sync) must
use the same convention for both the record and anything it references
(e.g. a `department` object) — a record written with a different tenant
prefix than expected becomes silently unreachable rather than wrongly
visible, which is the fail-closed direction to get wrong in, but still
worth avoiding.

Why ID namespacing instead of a `tenant` relation type: it requires no
change to the relation graph itself (owner/hr_admin/department/manager
logic is identical to the single-tenant version), and cross-tenant
collision is structurally impossible rather than dependent on every
relation path correctly propagating a tenant check through `manager from
department`-style traversals. The trade-off, made explicit above, is that
this alone doesn't stop a *tuple-writing* bug from crossing tenants — only
from ever making two tenants' identically-named records collide into the
same object.

## Authorization filtering (`glue/openfga_client.py`)

`OpenFgaFilter.filter_authorized(user_id, documents, tenant_id=...)`:

- Drops any document with no `tenant_id`, or (when the caller's
  `tenant_id` is supplied) a `tenant_id` that doesn't match, **before**
  calling OpenFGA at all.
- Builds the tenant-scoped object ID for every remaining document and
  issues **one** `batch_check` call instead of one `check` per document.
  The SDK bounds this internally: `max_batch_size` (default 50)
  checks per request, `max_parallel_requests` (default 10) concurrent
  requests — both overridable on `OpenFgaFilter.__init__` — so a large
  candidate set can't fan out into unbounded concurrent requests against
  OpenFGA.
- Fails closed at both levels: the SDK itself marks an individual failed
  check as `allowed=False`; if the whole `batch_check` call fails
  (OpenFGA unreachable, timeout, auth failure), `filter_authorized`
  catches it and returns an empty list — "authorize nothing" rather than
  raising and leaving the caller to guess whether a crash means "deny" or
  "unknown."

`tenant_id` is optional on `filter_authorized` only because it isn't
threaded through the pipeline's caller yet (that's the
authentication/tenant-isolation ticket) — a document is *always* required
to carry its own `tenant_id`; there's no path that authorizes a
tenant-less object.
