# Set.mm provider bootstrap artifact

This directory temporarily hosts the immutable
`metamath-setmm-provider==0.1.0` wheel required by the Stage 4 public
proof-source cohort.

- SHA-256:
  `421b8e8222577ebeb291382537aa4be0b1597aef88c5bde494973f0b13bfaa3d`
- Contents: 155 handle-only provider shards and no public proof functions.
- Source authority: `catalog-compiler` Stage 4 materialization.

The follow-up release work moves this artifact and its checked-in source into
the dedicated public `metamath-setmm-provider` repository. Consumers pin the
immutable commit containing this bootstrap artifact; no branch tip is used as
package identity.
