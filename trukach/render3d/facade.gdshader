shader_type spatial;
// Procedural rooftop buildings: concrete roof tiles on top, parapet band, windows (some lit) or brick on the walls.
// Works per-material (level blocks) or per-instance via INSTANCE_CUSTOM (background multimesh).

uniform vec3 wall_color : source_color = vec3(0.36, 0.33, 0.38);
uniform vec3 wall_color2 : source_color = vec3(0.22, 0.2, 0.25);
uniform vec3 roof_color : source_color = vec3(0.58, 0.55, 0.53);
uniform vec3 lit_color : source_color = vec3(1.0, 0.78, 0.46);
uniform vec3 glass_color : source_color = vec3(0.12, 0.17, 0.24);
uniform float top_y = 0.0;
uniform float lit_ratio = 0.22;
uniform float windows = 1.0;
uniform float brick = 0.0;
uniform float seed = 0.0;
uniform float use_custom = 0.0;
uniform float window_w = 1.0;

varying vec3 wpos;
varying vec3 wnrm;
varying vec4 cust;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	cust = INSTANCE_CUSTOM;
}

void fragment() {
	float ty = mix(top_y, cust.x, use_custom);
	float sd = mix(seed, cust.y, use_custom);
	float lr = mix(lit_ratio, cust.z, use_custom);
	vec3 col;
	float rough = 0.88;
	vec3 emit = vec3(0.0);
	if (wnrm.y > 0.5) {
		vec2 g = wpos.xz * 1.25;
		vec2 cell = floor(g);
		float n = hash(cell + sd);
		col = roof_color * (0.88 + 0.16 * n);
		vec2 fg = fract(g);
		float seam = max(step(fg.x, 0.025), step(fg.y, 0.025));
		col = mix(col, roof_color * 0.62, seam);
	} else if (wnrm.y < -0.5) {
		col = wall_color2 * 0.5;
	} else {
		float u = abs(wnrm.x) > 0.5 ? wpos.z : wpos.x;
		float dtop = ty - wpos.y;
		col = mix(wall_color2, wall_color, smoothstep(-9.0, 0.0, wpos.y - ty));
		if (brick > 0.5) {
			vec2 b = vec2(u * 4.0, wpos.y * 8.0);
			float row = floor(b.y);
			b.x += mod(row, 2.0) * 0.5;
			vec2 fb = fract(b);
			float mortar = max(step(fb.x, 0.06), step(fb.y, 0.1));
			col *= 0.9 + 0.2 * hash(floor(b) + sd);
			col = mix(col, col * 0.55, mortar);
		}
		if (dtop < 0.26) {
			col = roof_color * 0.82;
			if (dtop < 0.05) col = roof_color * 1.05;
		} else if (windows > 0.5 && dtop > 0.75) {
			vec2 w = vec2(u / window_w, (wpos.y - ty) / 1.3);
			vec2 cell = floor(w);
			vec2 fw = fract(w);
			if (fw.x > 0.2 && fw.x < 0.8 && fw.y > 0.18 && fw.y < 0.78) {
				float h = hash(cell + vec2(sd * 7.0, sd * 3.0));
				if (h < lr) {
					col = lit_color * 0.85;
					emit = lit_color * 1.1;
					rough = 0.4;
				} else {
					col = glass_color * (0.8 + 0.4 * hash(cell * 1.7 + sd));
					rough = 0.12;
				}
				if (abs(fw.x - 0.5) < 0.02) col *= 0.55;
			} else if (fw.y > 0.12 && fw.y < 0.18 && fw.x > 0.17 && fw.x < 0.83) {
				col *= 1.25;  // sill
			}
		}
	}
	ALBEDO = col;
	ROUGHNESS = rough;
	EMISSION = emit;
}
